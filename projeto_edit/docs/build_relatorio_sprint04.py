"""
build_relatorio_sprint04.py — gera relatorio_sprint04.pdf a partir dos resultados REAIS.

Pré-requisitos: rodar `python -m evaluation.run_eval` e `python -m evaluation.compare_manual`;
preencher evaluation/equipe.csv e (opcional) evaluation/analise_grupo.md
(seções "## Classificação", "## Comparação manual", "## Limitações" substituem os textos-padrão).
Recusa-se a gerar o PDF com dados de dry-run.
Uso: python docs/build_relatorio_sprint04.py
"""
import csv, json, os, re, sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EV = os.path.join(ROOT, "evaluation")
RES = os.path.join(EV, "results")
resumo = json.load(open(os.path.join(RES, "resumo.json"), encoding="utf-8"))
if resumo.get("dry_run"):
    sys.exit("resumo.json é de dry-run (dados falsos). Rode o pipeline de verdade.")
manual_path = os.path.join(RES, "comparacao_manual.json")
manual = json.load(open(manual_path, encoding="utf-8")) if os.path.exists(manual_path) else None
dataset = json.load(open(os.path.join(EV, "golden_dataset.json"), encoding="utf-8"))
equipe = list(csv.DictReader(open(os.path.join(EV, "equipe.csv"), encoding="utf-8")))
analise_path = os.path.join(EV, "analise_grupo.md")
analise = {}
if os.path.exists(analise_path):
    for bloco in re.split(r"^## ", open(analise_path, encoding="utf-8").read(), flags=re.M)[1:]:
        t, _, corpo = bloco.partition("\n")
        analise[t.strip().lower()] = corpo.strip()

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=colors.HexColor("#1a3d5c"), fontSize=15)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=colors.HexColor("#2c5f8a"), fontSize=12, spaceBefore=10)
B = ParagraphStyle("B", parent=ss["Normal"], fontSize=9.5, leading=13, spaceAfter=5)
C = ParagraphStyle("C", parent=ss["Normal"], fontSize=8, leading=10)
story = []
def h1(t): story.append(Paragraph(t, H1))
def h2(t): story.append(Paragraph(t, H2))
def p(t): story.append(Paragraph(t, B))
def tabela(rows, widths=None):
    t = Table([[Paragraph(str(c), C) for c in r] for r in rows], colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe7f3")),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t); story.append(Spacer(1, 6))

V = resumo["versoes"]; vs = list(V)
melhor = max(vs, key=lambda v: V[v]["nota_final"])
ranking = sorted(vs, key=lambda v: -V[v]["nota_final"])

h1("Relatório Final — Sprint 04 · EV Challenge GoodWe (ChargeGrid Intelligence)")
_rp = os.path.join(EV, "repo_url.txt")
_repo = open(_rp, encoding="utf-8").read().strip() if os.path.exists(_rp) else "[LINK DO REPOSITÓRIO FINAL: crie evaluation/repo_url.txt]"
p("Avaliação sistemática do agente: golden dataset, pipeline LLM as a judge e comparação entre versões. "
  f"Repositório da entrega: {_repo}. Sprints 1-2: github.com/IgorLDev/chargegrid-chatbot.")

h2("1. Golden dataset")
cont = {}
for d in dataset: cont[d["categoria"]] = cont.get(d["categoria"], 0) + 1
p(f"O dataset tem <b>{len(dataset)}</b> perguntas ({', '.join(f'{k}: {v}' for k, v in cont.items())}). "
  "Foi construído reaproveitando os casos de teste das Sprints 1 a 3 (coluna <i>origem</i> no arquivo) e expandido com casos "
  "novos: dados inexistentes na base (para medir alucinação), tarifas adicionais, uma paráfrase de prompt injection "
  "fora da lista de regex do guardrail, pergunta ambígua e memória combinada com RAG. Cada pergunta tem gabarito em texto, "
  "comportamento esperado (respondeu / recusou_ou_redirecionou / admitiu_sem_dado) e, quando há dado exato na base, termos "
  "obrigatórios ou proibidos para checagem determinística. Casos multi-turno enviam os turnos anteriores na mesma sessão.")

h2("2. Pipeline de avaliação")
p(f"Cada versão responde a todos os casos em <b>{resumo['reps']}</b> {'repetição' if resumo['reps'] == 1 else 'repetições'}, com sessões novas. Um LLM juiz "
  f"(<b>{resumo['juiz']}</b>, temperatura 0) recebe a base de conhecimento, a conversa, a resposta e o gabarito. "
  "Métricas: <b>Correção</b>, <b>Fidelidade ao contexto</b> e <b>Aderência ao escopo</b> (notas 0-5 do juiz, convertidas em 0-100); "
  "<b>Comportamento correto</b> (% de casos em que o comportamento classificado pelo juiz coincide com o esperado); "
  "<b>Taxa de recusa correta</b> (mesma métrica, só nos casos em que o esperado é recusar/redirecionar); "
  "<b>Acerto exato</b> (checagem determinística por termos, independente do juiz). "
  "<b>Nota final</b> = média simples, por avaliação, de correção, fidelidade, aderência e comportamento correto; depois média entre os casos e repetições. "
  "Respostas com falha de API são excluídas e contadas à parte.")

h2("3. Resultados por versão")
met = [("correcao", "Correção"), ("fidelidade_contexto", "Fidelidade ao contexto"), ("aderencia_escopo", "Aderência ao escopo"),
       ("comportamento_correto", "Comportamento correto (%)"), ("taxa_recusa_correta", "Taxa de recusa correta (%)"),
       ("acerto_exato", "Acerto exato determinístico (%)"), ("latencia_s", "Latência média (s)"),
       ("nota_final", "<b>NOTA FINAL</b>"), ("nota_final_std_entre_reps", "Desvio-padrão da nota entre repetições"),
       ("n_erros", "Avaliações com erro de API")]
tabela([["Métrica"] + vs] + [[n] + [("n/a" if V[v][k] is None else V[v][k]) for v in vs] for k, n in met])
cats = sorted({c for v in vs for c in resumo["por_categoria"][v]})
tabela([["Nota final por categoria"] + vs] + [[c] + [resumo["por_categoria"][v].get(c) for v in vs] for c in cats])

aud_path = os.path.join(RES, "resumo_auditado.json")
if os.path.exists(aud_path):
    aud = json.load(open(aud_path, encoding="utf-8")); av = list(aud)
    p("<b>Auditoria manual do juiz (repetição 1).</b> O grupo leu as respostas e corrigiu os casos em que o rótulo de "
      "comportamento do juiz contradizia a resposta (ver evaluation/correcoes_juiz.csv). A tabela compara as métricas "
      "dependentes desse rótulo antes e depois da auditoria.")
    ks = [("comportamento_correto_juiz", "Comportamento correto (%), juiz"), ("comportamento_correto_auditado", "Comportamento correto (%), auditado"),
          ("taxa_recusa_juiz", "Taxa de recusa correta (%), juiz"), ("taxa_recusa_auditada", "Taxa de recusa correta (%), auditada"),
          ("acerto_exato_corrigido", "Acerto exato (%), checagem corrigida")]
    tabela([["Métrica"] + av] + [[n] + [aud[v][k] for v in av] for k, n in ks])

h2("4. Classificação e justificativa")
rk = "; ".join(f"{i+1}º {v} ({V[v]['nota_final']})" for i, v in enumerate(ranking))
p(f"Ranking pela nota final: {rk}. Melhor versão: <b>{melhor}</b>.")
p(analise.get("classificação", "[O GRUPO DEVE ESCREVER: justificar a classificação com base nos números da tabela, "
  "citando as métricas e categorias em que as versões mais diferem. Escreva em evaluation/analise_grupo.md, seção '## Classificação'.]"))

h2("5. Comparação com a avaliação manual da Sprint 3")
if manual:
    p(f"Versão comparada: {manual['versao']}. Concordância em {manual['n']} casos: <b>{manual['concordancia_pct']}%</b> "
      f"(kappa de Cohen = {manual['kappa_cohen']}).")
    div = [i for i in manual["itens"] if not i["concorda"]]
    if div:
        tabela([["Caso", "Manual", "Pipeline", "Nota", "Justificativa do juiz"]] +
               [[i["id"], i["manual"], i["pipeline"], i["nota_pipeline"], i["justificativa_juiz"]] for i in div],
               [1.5*cm, 2*cm, 2*cm, 1.5*cm, 10*cm])
    else:
        p("Não houve divergências entre pipeline e avaliação manual.")
else:
    p("[Rode python -m evaluation.compare_manual para gerar esta seção.]")
p(analise.get("comparação manual", "[O GRUPO DEVE ESCREVER: hipóteses para cada divergência (ex.: avaliação manual da Sprint 3 baseada em "
  "palavras-chave vs. juiz semântico; rigor do juiz; variabilidade entre execuções).]"))

h2("6. Limitações do pipeline")
p(analise.get("limitações", "• Viés do LLM juiz: o juiz pode favorecer respostas do próprio provedor; recomenda-se repetir com JUDGE=openai e comparar. "
  "• Cobertura: " + f"{len(dataset)} casos e uma base de conhecimento de apenas 2 arquivos (o RAG recupera praticamente tudo), logo o dataset mede pouco a qualidade da recuperação. "
  "• Variabilidade: respostas de LLM variam entre execuções; por isso são usadas repetições e reportado o desvio-padrão. "
  "• A versão da Sprint 2 foi avaliada com a base .txt da Sprint 3 e sem temperatura fixa (como no original), o que também difere da Sprint 3. "
  "• Custo/latência: cada rodada completa faz centenas de chamadas de API."))

h2("7. Equipe e divisão de trabalho")
tabela([["Nome", "RM", "Tarefa principal"]] + [[e["nome"], e["rm"], e["tarefa"] or "[PREENCHER em evaluation/equipe.csv]"] for e in equipe],
       [6*cm, 3*cm, 8*cm])

out = os.path.join(ROOT, "relatorio_sprint04.pdf")
SimpleDocTemplate(out, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm).build(story)
print("Gerado:", out)
