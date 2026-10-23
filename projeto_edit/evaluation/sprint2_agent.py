"""
sprint2_agent.py
Reprodução fiel da versão das Sprints 1-2 (chatbot_goodwe.py, repositório
github.com/IgorLDev/chargegrid-chatbot) como classe, para poder ser avaliada
pelo mesmo pipeline da versão da Sprint 3.

Preservado do original: grafo linear add_sequence([retrieve, generate]),
SYSTEM_PROMPT da Sprint 2 (2 frases, sem listas), histórico gerenciado "na mão"
(lista chat_history repassada a cada chamada), gpt-4o-mini sem temperature fixa.

Única adaptação (decisão metodológica, citar no relatório): a base de
conhecimento é a MESMA da Sprint 3 (knowledge_base/*.txt), para que a
comparação meça a arquitetura/prompt e não diferenças de documentos.
"""
import os
from pathlib import Path
from typing import List, TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph

from app.config import require_api_key

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")

SYSTEM_PROMPT_S2 = """
Você é o Chatbot GoodWe, assistente operacional do ChargeGrid Intelligence no contexto do EV Challenge 2026.

Regras:
- Responda sempre em português do Brasil.
- Seja extremamente objetivo.
- Utilize no máximo 2 frases curtas.
- Não use listas.
- Utilize o histórico da conversa para compreender referências como "esse valor", "isso" e "o resultado anterior".
- Perguntas sobre sua função ou capacidades podem ser respondidas usando sua descrição institucional.
- Quando houver um dado exato no contexto recuperado, informe apenas o dado relevante.
- Nunca invente valores ou registros que não estejam presentes no contexto.
- Quando não houver dados suficientes, informe que o valor exato não foi encontrado e oriente brevemente como obtê-lo.
- Não ofereça ajuda adicional ao final da resposta.

Você auxilia operadores comerciais com dúvidas sobre potência, faturamento, ciclos de carregamento, comunicação com usuários e gestão de horários de pico.
"""


class State(TypedDict):
    question: str
    context: List[Document]
    answer: str
    chat_history: List[dict]


class Sprint2Agent:
    def __init__(self, provider: str = "openai"):
        """provider="openai": gpt-4o-mini como no original. provider="google": Gemini (gratuito)."""
        self.no_embeddings = os.getenv("EMBEDDINGS_PROVIDER", "openai") == "none"
        if provider == "compat":
            require_api_key("compat")
            self.llm = ChatOpenAI(model=os.getenv("COMPAT_MODEL", "llama3.1:8b"),
                                  base_url=os.getenv("COMPAT_BASE_URL", "http://localhost:11434/v1"),
                                  api_key=os.getenv("COMPAT_API_KEY"))
        elif provider == "google":
            require_api_key("google")
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))  # sem temperature, como no original
        else:
            require_api_key("openai")
            self.llm = ChatOpenAI(model="gpt-4o-mini")  # init_chat_model("gpt-4o-mini") no original
        docs = []
        for p in sorted(Path(KB_DIR).glob("*.txt")):
            docs.extend(TextLoader(str(p), encoding="utf-8").load())
        splits = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, add_start_index=True
        ).split_documents(docs)
        if self.no_embeddings:
            self.all_splits = splits  # equivalente ao k=2 com a base atual (2 arquivos)
        else:
            require_api_key("openai")
            self.vector_store = InMemoryVectorStore(OpenAIEmbeddings(model="text-embedding-3-small"))
            self.vector_store.add_documents(splits)

        builder = StateGraph(State).add_sequence([self._retrieve, self._generate])
        builder.add_edge(START, "_retrieve")
        self.graph = builder.compile()
        self._histories: dict[str, list] = {}  # histórico manual por "sessão"

    def _retrieve(self, state: State):
        if self.no_embeddings:
            return {"context": self.all_splits}
        return {"context": self.vector_store.similarity_search(state["question"], k=2)}

    def _generate(self, state: State):
        docs_content = "\n\n".join(d.page_content for d in state["context"])
        messages = [{"role": "system", "content": SYSTEM_PROMPT_S2}]
        messages.extend(state.get("chat_history", []))
        messages.append({"role": "user", "content": (
            f"""
Pergunta do usuário: {state['question']}
Contexto recuperado: {docs_content if docs_content else "Nenhum contexto recuperado."}
Utilize o contexto recuperado quando a pergunta exigir dados, registros ou informações presentes nos documentos
Perguntas sobre sua identidade, função, objetivo ou capacidades podem ser respondidas usando sua descrição institucional.
""")})
        response = self.llm.invoke(messages)
        hist = state.get("chat_history", []).copy()
        hist.append({"role": "user", "content": state["question"]})
        hist.append({"role": "assistant", "content": response.content})
        return {"answer": response.content, "chat_history": hist}

    def send(self, session_id: str, user_message: str) -> str:
        hist = self._histories.get(session_id, [])
        result = self.graph.invoke({"question": user_message, "chat_history": hist})
        self._histories[session_id] = result["chat_history"]
        return result["answer"]
