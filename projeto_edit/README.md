# GoodWe EV Challenge — Sprint 03

Agente conversacional GoodWe reconstruído com **LangGraph**, com memória
por sessão, guardrails de segurança e comparação entre modelos de linguagem.

## O que mudou em relação às Sprints 1 e 2

A Sprint 1-2 (repositório original: `chargegrid-chatbot`) já usava LangGraph,
mas de forma mínima: um `add_sequence([retrieve, generate])` linear, sem nós
de decisão, com histórico de conversa numa lista Python comum e RAG sobre
PDFs/Word em `./docs`. A persona é o **operador comercial do ChargeGrid
Intelligence** (potência, faturamento, ciclos de carregamento) — mantida
nesta Sprint 03.

| Antes (Sprints 1-2) | Agora (Sprint 03) |
|---|---|
| Grafo linear (`add_sequence`), sem nós de decisão | Grafo ramificado: guardrail de entrada → retrieve → llm |
| Histórico gerenciado "na mão" (lista `chat_history`) | Memória por sessão nativa do framework (`MemorySaver`, por `thread_id`) |
| RAG sobre PDF/Word em `./docs` | RAG mantido (nó `retrieve`), agora também com `.txt/.md` em `knowledge_base/` |
| Segurança dependia só do texto do system prompt | Guardrail de entrada (regex) + guardrail de saída, além do system prompt |
| Um único modelo fixo (gpt-4o-mini), sem comparação | Configuração plugável (`app/config.py:MODEL_CONFIGS`), testado com 2+ modelos |

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edite o .env com suas chaves reais
```

**Importante:** a busca em documentos (RAG) usa `OpenAIEmbeddings`, herdado
da Sprint 1-2. Isso significa que `OPENAI_API_KEY` é necessária **mesmo se
você testar o modelo de chat da Anthropic/Google** — só o modelo que gera a
resposta final muda; a busca de contexto continua sempre via OpenAI.

## Rodando o chat

```bash
python -m app.main
python -m app.main --model anthropic_claude
```

## Rodando os testes

```bash
# Testes funcionais
pytest tests/test_functional.py -v

# Testes de memória (reproduz o exemplo do enunciado: condomínio + vagas)
pytest tests/test_memory.py -v

# Testes de segurança / prompt injection
pytest tests/test_security.py -v -s
```

Os testes de segurança geram um log em `logs/security_test_results.jsonl`
com o veredito (`passed: true/false`) e uma nota de análise para cada caso —
use isso para preencher a seção 4 do relatório de evolução.

## Comparação entre modelos (Requisito 5)

```bash
python -m tests.run_model_comparison
```

Isso roda o mesmo conjunto de casos (funcional + memória + segurança) em
cada modelo listado em `app/config.py:MODEL_CONFIGS` e salva os dados
brutos (latência, tamanho de resposta, erros) em
`results/model_comparison_raw.json`.

**Importante:** esses números precisam ser gerados rodando o script de
verdade com suas próprias chaves de API — eles não podem ser inventados,
pois a rubrica exige resultados reais de experimentação. Depois de rodar,
preencha `relatorio_modelos.md` com os números obtidos.

## Estrutura

```
app/
  config.py       -> system prompt (persona: operador comercial), configs de modelo
  guardrails.py   -> detecção de prompt injection e validação de saída
  memory.py       -> memória por sessão (checkpointer do LangGraph)
  rag.py          -> recuperação de contexto (RAG) sobre knowledge_base/
  agent.py        -> grafo do agente (LangGraph): guardrail → retrieve → llm
  main.py         -> CLI de chat
knowledge_base/   -> documentos de exemplo (potência, faturamento, ciclos)
tests/
  test_functional.py
  test_memory.py
  test_security.py
  run_model_comparison.py
relatorio_modelos.md
integrantes.txt
```

## Equipe

Ver `integrantes.txt`.

## Sprint 04 — Avaliação sistemática (`evaluation/`)

Pipeline que substitui a checagem manual por métricas reprodutíveis, comparando
Sprint 2 (`s2`), Sprint 3 com gpt-4o-mini (`s3`) e Sprint 3 com Claude (`s3c`).

```bash
python -m evaluation.run_eval --dry-run          # testa o encanamento sem chaves (dados FALSOS)
python -m evaluation.run_eval                    # execução real (OPENAI_API_KEY + ANTHROPIC_API_KEY no .env)
# preencha evaluation/avaliacao_manual_sprint3.csv com os vereditos da Sprint 3
python -m evaluation.compare_manual
# preencha evaluation/equipe.csv (e, se quiser, evaluation/analise_grupo.md)
python docs/build_relatorio_sprint04.py          # gera relatorio_sprint04.pdf
```

Arquivos: `golden_dataset.json` (24 casos com gabarito), `sprint2_agent.py` (versão da Sprint 2 como
classe), `judge.py` (LLM juiz), `run_eval.py`, `compare_manual.py`. Resultados em `evaluation/results/`.
Para checar viés do juiz: `JUDGE=openai python -m evaluation.run_eval`.

### Sem chave paga (caminho gratuito)

Crie uma `GOOGLE_API_KEY` grátis no Google AI Studio (só conta Google) e rode:

```bash
export GOOGLE_API_KEY=sua_chave EMBEDDINGS_PROVIDER=none JUDGE=google CALL_DELAY=6
python -m evaluation.run_eval --versions s2g s3g --reps 1
```

`EMBEDDINGS_PROVIDER=none` dispensa a OpenAI no RAG (devolve todos os trechos; equivale à busca
atual porque a base tem 2 arquivos e k=2). Se o nome do modelo mudar, ajuste `GEMINI_MODEL`.

### Sem nenhuma conta/pagamento (modelo local com Ollama)

1. Instale o Ollama (ollama.com) e rode `ollama pull llama3.1:8b` (~5 GB; precisa de ~8 GB de RAM).
2. Com o Ollama aberto, defina no `.env`: `COMPAT_API_KEY=ollama`, `COMPAT_MODEL=llama3.1:8b`,
   `EMBEDDINGS_PROVIDER=none`, `JUDGE=compat`.
3. `python -m evaluation.run_eval --versions s2o s3o --reps 1`

Também funciona com Groq/OpenRouter: defina `COMPAT_BASE_URL`, `COMPAT_API_KEY` e `COMPAT_MODEL` do serviço.
Um modelo local pequeno é juiz mais fraco: registre isso nas limitações do relatório.

### Auditoria do juiz (após rodar a avaliação)

O juiz local pode errar o rótulo de comportamento. Leia as respostas em `evaluation/results/resultados.csv`,
confira/ajuste `evaluation/correcoes_juiz.csv` e rode `python -m evaluation.auditoria`
(gera `results/resumo_auditado.md`, usado automaticamente pelo gerador do PDF).
