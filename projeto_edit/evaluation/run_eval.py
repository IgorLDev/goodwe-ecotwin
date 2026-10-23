"""
run_eval.py — Pipeline de avaliação sistemática (Sprint 04).

Executa o golden dataset contra cada versão do agente, julga cada resposta
(LLM as a judge + checagens determinísticas) e calcula as métricas.

Uso (na raiz do repositório):
    python -m evaluation.run_eval                      # 3 versões, 3 repetições
    python -m evaluation.run_eval --reps 1             # mais barato
    python -m evaluation.run_eval --versions s2 s3     # só duas versões
    python -m evaluation.run_eval --dry-run            # testa o encanamento SEM chaves
                                                       # (dados FALSOS, saída em results/dryrun/)

Versões: s2 = Sprint 2 (gpt-4o-mini) | s3 = Sprint 3 (gpt-4o-mini) | s3c = Sprint 3 (claude-sonnet-4-5)
         s2g / s3g = Sprint 2 / Sprint 3 com Gemini (OPÇÃO GRATUITA, só GOOGLE_API_KEY):
    export GOOGLE_API_KEY=... EMBEDDINGS_PROVIDER=none JUDGE=google CALL_DELAY=6
    python -m evaluation.run_eval --versions s2g s3g --reps 1
         s2o / s3o = Sprint 2 / Sprint 3 com modelo LOCAL (Ollama) ou qualquer API compatível com OpenAI
         (Groq, OpenRouter...), sem OpenAI/Google:
    COMPAT_API_KEY=ollama COMPAT_MODEL=llama3.1:8b EMBEDDINGS_PROVIDER=none JUDGE=compat
    python -m evaluation.run_eval --versions s2o s3o --reps 1
Chaves via .env / variáveis de ambiente (nunca no código).
"""
import argparse, csv, json, os, statistics, sys, time, uuid
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

DATASET = os.path.join(HERE, "golden_dataset.json")
API_FAILURE_PREFIX = "Estou com uma instabilidade temporária"

VERSION_LABELS = {
    "s2": "Sprint 2 (gpt-4o-mini)",
    "s3": "Sprint 3 (gpt-4o-mini)",
    "s3c": "Sprint 3 (claude-sonnet-4-5)",
    "s2g": "Sprint 2 (Gemini)",
    "s3g": "Sprint 3 (Gemini)",
    "s2o": "Sprint 2 (modelo local/compat)",
    "s3o": "Sprint 3 (modelo local/compat)",
}
METRICAS = ["correcao", "fidelidade_contexto", "aderencia_escopo", "comportamento_correto"]
METRICA_NOMES = {
    "correcao": "Correção (juiz, 0-100)",
    "fidelidade_contexto": "Fidelidade ao contexto (juiz, 0-100)",
    "aderencia_escopo": "Aderência ao escopo (juiz, 0-100)",
    "comportamento_correto": "Comportamento correto (%)",
    "acerto_exato": "Acerto exato determinístico (%)",
    "taxa_recusa_correta": "Taxa de recusa correta (%)",
    "latencia_s": "Latência média do último turno (s)",
    "nota_final": "NOTA FINAL (0-100)",
}


# ----------------------------- versões do agente -----------------------------
def make_agent(key: str, dry: bool):
    if dry:
        return DryAgent(key)
    if key in ("s2", "s2g", "s2o"):
        from evaluation.sprint2_agent import Sprint2Agent
        return Sprint2Agent(provider={"s2": "openai", "s2g": "google", "s2o": "compat"}[key])
    from app.agent import GoodWeAgent
    return GoodWeAgent(model_key={"s3": "openai_gpt4o_mini", "s3c": "anthropic_claude", "s3g": "google_gemini", "s3o": "compat"}[key])


class DryAgent:
    """Agente FALSO só para validar o pipeline sem chaves de API."""
    def __init__(self, key): self.key = key
    def send(self, session_id, msg):
        return "Resposta fictícia de teste (dry-run). 51 kW 19h 2,10 13.020 27 24 12 4 kW 24h 1,60 1,10"


def dry_judge(llm, kb, turnos, resposta, gabarito):
    return {"correcao": 4, "fidelidade_contexto": 5, "aderencia_escopo": 5,
            "comportamento": "respondeu", "justificativa": "dry-run (dados falsos)"}


# ----------------------------- checagens determinísticas ---------------------
def _norm(t: str) -> str:
    # ignora espaços e separadores decimais/milhar ("1,10" == "1.10"; "13.020" == "13020")
    return t.lower().replace(" ", "").replace(".", "").replace(",", "")


def acerto_exato(item: dict, resposta: str):
    termos = item.get("esperado_contem_todos")
    proibidos = item.get("proibido_conter")
    if not termos and not proibidos:
        return None
    r = _norm(resposta)
    ok = all(_norm(t) in r for t in (termos or []))
    ok = ok and not any(_norm(p) in r for p in (proibidos or []))
    return int(ok)


# ----------------------------- execução --------------------------------------
def run_case(agent, item, tag):
    delay = float(os.getenv("CALL_DELAY", "0"))  # use ~6 no plano gratuito do Gemini (limite de RPM)
    for tentativa in range(3):
        session = f"eval-{tag}-{item['id']}-{uuid.uuid4().hex[:8]}"
        resposta, erro, lat = "", None, 0.0
        try:
            for turno in item["turnos"]:
                time.sleep(delay)
                t0 = time.perf_counter()
                resposta = agent.send(session, turno)
                lat = time.perf_counter() - t0
        except Exception as e:
            erro = str(e)
        if erro is None and resposta.startswith(API_FAILURE_PREFIX):
            erro = "falha de API (mensagem de fallback do agente)"
        if erro is None:
            break
        time.sleep(15 * (tentativa + 1))  # backoff antes de tentar de novo (ex.: erro 429)
    return resposta, erro, lat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--versions", nargs="+", default=["s2", "s3", "s3c"], choices=list(VERSION_LABELS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out_dir = os.path.join(HERE, "results", "dryrun" if args.dry_run else "")
    os.makedirs(out_dir, exist_ok=True)
    dataset = json.load(open(DATASET, encoding="utf-8"))

    if args.dry_run:
        judge_fn, llm, kb, judge_name = dry_judge, None, "", "dry-run"
    else:
        from evaluation.judge import judge as judge_fn, build_judge_llm, load_kb
        llm, kb = build_judge_llm(), load_kb()
        judge_name = f"{os.getenv('JUDGE', 'anthropic')}:{getattr(llm, 'model', None) or getattr(llm, 'model_name', '?')}"

    linhas = []
    for key in args.versions:
        label = VERSION_LABELS[key]
        agent = make_agent(key, args.dry_run)
        for rep in range(1, args.reps + 1):
            for item in dataset:
                resposta, erro, lat = run_case(agent, item, f"{key}-r{rep}")
                row = {"versao": label, "rep": rep, "id": item["id"], "categoria": item["categoria"],
                       "resposta": resposta, "erro": erro or "", "latencia_s": round(lat, 3),
                       "comportamento_esperado": item["comportamento_esperado"]}
                if erro:
                    row.update({m: "" for m in ["correcao", "fidelidade_contexto", "aderencia_escopo",
                                                "comportamento_observado", "comportamento_correto",
                                                "acerto_exato", "nota_final", "justificativa"]})
                else:
                    v = judge_fn(llm, kb, item["turnos"], resposta, item["gabarito"])
                    cc = int(v["comportamento"] == item["comportamento_esperado"])
                    row.update({
                        "correcao": v["correcao"], "fidelidade_contexto": v["fidelidade_contexto"],
                        "aderencia_escopo": v["aderencia_escopo"], "comportamento_observado": v["comportamento"],
                        "comportamento_correto": cc, "acerto_exato": acerto_exato(item, resposta),
                        "justificativa": v["justificativa"],
                        "nota_final": round(100 * statistics.mean(
                            [v["correcao"] / 5, v["fidelidade_contexto"] / 5, v["aderencia_escopo"] / 5, cc]), 1),
                    })
                if row.get("acerto_exato") is None:
                    row["acerto_exato"] = ""
                linhas.append(row)
                print(f"[{label}] rep{rep} {item['id']} -> nota {row.get('nota_final')} {('ERRO: ' + erro) if erro else ''}")

    # ---------------- agregação ----------------
    def mean_of(rows, col, scale=1.0):
        vals = [float(r[col]) for r in rows if r[col] not in ("", None)]
        return round(scale * statistics.mean(vals), 1) if vals else None

    resumo = {"dry_run": args.dry_run, "reps": args.reps, "juiz": judge_name, "n_casos": len(dataset),
              "versoes": {}, "por_categoria": {}}
    for label in [VERSION_LABELS[k] for k in args.versions]:
        rows = [r for r in linhas if r["versao"] == label]
        ok = [r for r in rows if not r["erro"]]
        recusa = [r for r in ok if r["comportamento_esperado"] == "recusou_ou_redirecionou"]
        por_rep = [mean_of([r for r in ok if r["rep"] == k], "nota_final") for k in range(1, args.reps + 1)]
        por_rep = [x for x in por_rep if x is not None]
        resumo["versoes"][label] = {
            "correcao": mean_of(ok, "correcao", 20), "fidelidade_contexto": mean_of(ok, "fidelidade_contexto", 20),
            "aderencia_escopo": mean_of(ok, "aderencia_escopo", 20),
            "comportamento_correto": mean_of(ok, "comportamento_correto", 100),
            "acerto_exato": mean_of(ok, "acerto_exato", 100),
            "taxa_recusa_correta": mean_of(recusa, "comportamento_correto", 100),
            "latencia_s": mean_of(ok, "latencia_s"),
            "nota_final": mean_of(ok, "nota_final"),
            "nota_final_std_entre_reps": round(statistics.pstdev(por_rep), 2) if len(por_rep) > 1 else None,
            "n_avaliacoes": len(ok), "n_erros": len(rows) - len(ok),
        }
        resumo["por_categoria"][label] = {
            cat: mean_of([r for r in ok if r["categoria"] == cat], "nota_final")
            for cat in sorted({r["categoria"] for r in ok})}

    campos = ["versao", "rep", "id", "categoria", "comportamento_esperado", "comportamento_observado", "correcao",
              "fidelidade_contexto", "aderencia_escopo", "comportamento_correto", "acerto_exato", "nota_final",
              "latencia_s", "erro", "justificativa", "resposta"]
    with open(os.path.join(out_dir, "resultados.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader(); w.writerows(linhas)
    json.dump(resumo, open(os.path.join(out_dir, "resumo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    vs = list(resumo["versoes"])
    md = ["| Métrica | " + " | ".join(vs) + " |", "|---|" + "---|" * len(vs)]
    for m in ["correcao", "fidelidade_contexto", "aderencia_escopo", "comportamento_correto", "acerto_exato",
              "taxa_recusa_correta", "latencia_s", "nota_final"]:
        md.append(f"| {METRICA_NOMES[m]} | " + " | ".join(str(resumo["versoes"][v][m]) for v in vs) + " |")
    md += ["", "| Nota final por categoria | " + " | ".join(vs) + " |", "|---|" + "---|" * len(vs)]
    cats = sorted({c for v in vs for c in resumo["por_categoria"][v]})
    for c in cats:
        md.append(f"| {c} | " + " | ".join(str(resumo["por_categoria"][v].get(c)) for v in vs) + " |")
    if args.dry_run:
        md.insert(0, "> **DRY-RUN: DADOS FALSOS. NÃO USAR NO RELATÓRIO.**\n")
    open(os.path.join(out_dir, "resumo.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n" + "\n".join(md))
    print(f"\nSalvo em {out_dir}")


if __name__ == "__main__":
    main()
