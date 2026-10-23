"""
build_relatorio_evolucao.py
Gera relatorio_evolucao.pdf (Requisito 7), com no máximo 5 páginas.

Métricas sem evidência nos arquivos fornecidos são identificadas como não medidas; não são inventados resultados.

Uso:
    python docs/build_relatorio_evolucao.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
)

OUTPUT_PATH = "relatorio_evolucao.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], spaceAfter=8, spaceBefore=4, textColor=colors.HexColor("#1a3d5c")))
styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], spaceAfter=6, spaceBefore=10, textColor=colors.HexColor("#2c5f8a")))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallItalic", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.grey, spaceAfter=4))

story = []

def h1(text):
    story.append(Paragraph(text, styles["H1Custom"]))

def h2(text):
    story.append(Paragraph(text, styles["H2Custom"]))

def body(text):
    story.append(Paragraph(text, styles["BodyCustom"]))

def note(text):
    story.append(Paragraph(text, styles["SmallItalic"]))

def bullets(items):
    story.append(ListFlowable(
        [ListItem(Paragraph(i, styles["BodyCustom"])) for i in items],
        bulletType="bullet", start="•", leftIndent=14,
    ))

# ---------------------------------------------------------------------
# Capa / Título
# ---------------------------------------------------------------------
h1("Relatório de Evolução — EV Challenge GoodWe (Sprint 03)")
body(
    "Disciplina: Prompt and Artificial Intelligence &nbsp;|&nbsp; "
    "Curso: Ciência da Computação — 1º ano &nbsp;|&nbsp; Parceiro: GoodWe Brasil"
)
note(
    "Repositório Sprint 1-2: github.com/IgorLDev/chargegrid-chatbot &nbsp;|&nbsp; "
    "Equipe: ver integrantes.txt (turma CCPW)."
)
story.append(Spacer(1, 10))

# ---------------------------------------------------------------------
# 7.1 Resumo da evolução
# ---------------------------------------------------------------------
h2("1. Resumo da evolução (Sprints 1-2 → Sprint 03)")
body(
    "Nas Sprints 1 e 2, o chatbot ChargeGrid Intelligence (persona: operador "
    "comercial de eletropostos) já utilizava <b>LangGraph</b>, mas de forma mínima: "
    "um único <i>add_sequence([retrieve, generate])</i>, sem nós de decisão, sem "
    "guardrails, e com o histórico de conversa mantido numa lista Python comum "
    "(<i>chat_history</i>) repassada manualmente a cada chamada. A recuperação de "
    "contexto (RAG) já existia, buscando em documentos PDF/Word com "
    "OpenAIEmbeddings + InMemoryVectorStore, usando gpt-4o-mini como único modelo, "
    "sem comparação com outros."
)
body(
    "Na Sprint 03, o mesmo framework foi mantido, mas aprofundado: o fluxo passou a "
    "ter um nó de <b>decisão explícito</b> (guardrail de entrada, capaz de encerrar o "
    "grafo antes de chamar o LLM), a memória por sessão passou a ser gerenciada pelo "
    "mecanismo <b>nativo</b> do LangGraph (checkpointer, indexado por thread_id, com "
    "isolamento comprovado entre sessões diferentes), e o RAG foi mantido como um nó "
    "próprio do grafo (retrieve), agora suportando também arquivos .txt/.md."
)
body(
    "Além disso, foram adicionados: (i) uma camada de guardrails independente do "
    "modelo, capaz de bloquear tentativas óbvias de prompt injection antes mesmo de "
    "chamar a LLM; (ii) um conjunto formal de casos de teste de segurança "
    "(inexistente nas Sprints 1-2); e (iii) um processo de comparação experimental "
    "entre dois modelos de linguagem diferentes para escolher o modelo final com "
    "base em dados, não em preferência (nas Sprints 1-2 o modelo era fixo, sem "
    "experimentação)."
)

# ---------------------------------------------------------------------
# 7.2 Refatoração
# ---------------------------------------------------------------------
h2("2. Refatoração: decisões técnicas e trade-offs")
body("<b>Framework escolhido:</b> LangGraph.")
bullets([
    "Modela o agente como grafo de estados, o que dá controle explícito sobre o fluxo "
    "conversacional (nós de guardrail de entrada, chamada ao LLM e guardrail de saída), "
    "em vez de uma função monolítica.",
    "Gerenciamento de memória por sessão nativo via <i>checkpointer</i> "
    "(<i>MemorySaver</i>/<i>SqliteSaver</i>), atendendo ao requisito de memória sem "
    "reimplementar buffer de histórico manualmente.",
    "Agnóstico de provedor de LLM (usa os wrappers de chat model do LangChain por baixo), "
    "o que facilitou testar múltiplos modelos apenas trocando uma chave de configuração.",
])
body("<b>Principais trade-offs identificados:</b>")
bullets([
    "Curva de aprendizado maior que uma chamada direta de API — para um agente único e "
    "simples como este, parte da estrutura de grafo é overhead; o ganho aparece mais "
    "claramente se o projeto crescer (mais ferramentas, mais nós de decisão).",
    "A defesa de prompt injection combina duas camadas (regras no system prompt + filtro "
    "de regex no código). A camada de regex é rígida — pega variações conhecidas, mas não "
    "generaliza para frases nunca vistas — então a robustez real depende também da "
    "obediência do modelo às instruções do system prompt.",
    "Outro problema técnico específico não foi registrado nos arquivos fornecidos; por isso, não foi atribuído um problema hipotético ao grupo.",
])

# ---------------------------------------------------------------------
# 7.3 Comparativo antes x depois
# ---------------------------------------------------------------------
h2("3. Comparativo antes × depois")
data = [
    ["Critério", "Sprints 1-2 (legado)", "Sprint 03 (evolução)"],
    ["Arquitetura", "LangGraph com add_sequence linear (retrieve→generate), sem nós de decisão", "LangGraph com grafo ramificado: guardrail de entrada → retrieve → llm"],
    ["Memória", "Lista Python manual (chat_history), repassada à mão a cada chamada", "Checkpointer nativo do LangGraph, isolado por sessão (thread_id)"],
    ["RAG / base de conhecimento", "PDF/Word em ./docs, PyPDFLoader/UnstructuredWordDocumentLoader", "Mantido (retrieve como nó do grafo), + suporte a .txt/.md em knowledge_base/"],
    ["Segurança", "Apenas regras soltas no system prompt, sem testes formais", "System prompt + guardrail de entrada/saída no código + suíte de testes"],
    ["Modelo", "gpt-4o-mini fixo, sem comparação", "Não definido: a comparação entre provedores ainda não foi executada."],
    ["Nota testes funcionais", "Não havia testes formais documentados", "Funcionalidade: 100% na avaliação comparativa (24 casos; modelo local/compat)."],
    ["Nota testes de memória (3+ turnos)", "Não havia testes formais documentados", "Categoria memória: 100% na avaliação comparativa (24 casos; modelo local/compat)."],
    ["Nota testes de segurança", "Não havia testes formais documentados", "Categoria segurança: 65,0 → 70,8; taxa de recusa correta do juiz: 50,0% → 60,0% (modelo local/compat)."],
    ["Tokens médios por turno", "Não medido no material disponível", "Não medido no material disponível"],
    ["Latência média por turno", "250,6 s (último turno, avaliação local/compat)", "81,3 s (último turno, avaliação local/compat)"],
]
tbl = Table(data, colWidths=[4.5*cm, 5.5*cm, 6.5*cm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3d5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(tbl)
story.append(Spacer(1, 6))
note(
    "Os resultados de latência e categorias foram extraídos de evaluation/results/resumo.json "
    "e se referem à avaliação comparativa Sprint 2 × Sprint 3 com modelo local/compat. "
    "Não são métricas da comparação gpt-4o-mini × claude-sonnet-4-5. Tokens por turno não foram registrados."
)
body(
    "<b>A nova arquitetura realmente tornou o chatbot melhor?</b> Sim, os resultados disponíveis "
    "indicam melhora geral na avaliação local/compat: a nota final subiu de 82,9 para 87,3 "
    "(+4,4 pontos), a fidelidade ao contexto foi de 91,7 para 95,8, e a latência média do último "
    "turno caiu de 250,6 s para 81,3 s. A categoria de segurança subiu de 65,0 para 70,8. "
    "Esses resultados apoiam uma melhora, mas não substituem a comparação experimental entre "
    "os dois provedores de LLM."
)

story.append(PageBreak())

# ---------------------------------------------------------------------
# 7.4 Problemas encontrados e soluções
# ---------------------------------------------------------------------
h2("4. Problemas encontrados e soluções")

h2_style_small = styles["BodyCustom"]

def problema_bloco(numero, problema, alternativas, solucao, justificativa):
    body(f"<b>Problema {numero}:</b> {problema}")
    body(f"<b>Alternativas consideradas:</b> {alternativas}")
    body(f"<b>Solução adotada:</b> {solucao}")
    body(f"<b>Justificativa:</b> {justificativa}")
    story.append(Spacer(1, 4))

problema_bloco(
    1,
    "Garantir que o histórico de conversa de uma sessão não vazasse para outra "
    "sessão (isolamento de memória entre usuários diferentes).",
    "(a) manter um dicionário global de histórico indexado por usuário no próprio "
    "código da aplicação; (b) usar o checkpointer nativo do LangGraph indexado por "
    "thread_id.",
    "Opção (b): uso do checkpointer nativo (MemorySaver) do LangGraph, com "
    "thread_id = session_id.",
    "Reduz código customizado propenso a bugs de isolamento e delega a "
    "responsabilidade de persistência/isolamento ao framework, que já foi testado "
    "para esse fim. Validado pelo teste automatizado "
    "test_memory_isolada_por_sessao.",
)

problema_bloco(
    2,
    "A Sprint 1-2 não tinha nenhuma defesa formal contra prompt injection — o "
    "system prompt continha regras de comportamento, mas nada impedia que o "
    "modelo fosse convencido a ignorá-las.",
    "(a) confiar apenas na instrução de segurança dentro do próprio system prompt; "
    "(b) adicionar uma camada de guardrail no código, independente do modelo, que "
    "filtra padrões conhecidos de manipulação antes mesmo de chamar a LLM.",
    "Opção (b), combinada com (a): guardrail de entrada por regex "
    "(app/guardrails.py) somado às instruções no system prompt, seguindo o "
    "princípio de defesa em profundidade.",
    "Depender só do modelo é frágil — resultados variam entre modelos e podem "
    "mudar com atualizações do provedor. Uma camada determinística no código dá "
    "uma garantia adicional, mensurável pelos testes automatizados de segurança "
    "(ver test_security.py).",
)

body(
    "Problema 3 (opcional): não há registro de outro problema técnico específico nos arquivos fornecidos."
)

# ---------------------------------------------------------------------
# 7.5 Divisão da equipe
# ---------------------------------------------------------------------
h2("5. Divisão da equipe")
team_data = [
    ["Nome", "RM", "Principal responsabilidade"],
    ["Guilherme Detta", "569666", "Responsabilidade individual na Sprint 03 não documentada nos arquivos fornecidos."],
    ["Igor Alves", "574127", "Responsabilidade individual na Sprint 03 não documentada nos arquivos fornecidos."],
    ["Henrique Bolfer", "569514", "Responsabilidade individual na Sprint 03 não documentada nos arquivos fornecidos."],
    ["Arthur Costa", "569976", "Responsabilidade individual na Sprint 03 não documentada nos arquivos fornecidos."],
    ["Rafaella Ferreira", "571030", "Responsabilidade individual na Sprint 03 não documentada nos arquivos fornecidos."],
    ["Aneliza Rondina", "572977", "Responsabilidade individual na Sprint 03 não documentada nos arquivos fornecidos."],
]
team_tbl = Table(team_data, colWidths=[5.5*cm, 3*cm, 8*cm])
team_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3d5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(team_tbl)

doc = SimpleDocTemplate(
    OUTPUT_PATH, pagesize=A4,
    topMargin=1.7*cm, bottomMargin=1.7*cm, leftMargin=1.8*cm, rightMargin=1.8*cm,
)
doc.build(story)
print(f"PDF gerado em: {OUTPUT_PATH}")
