"""
auditoria.py — corrige o viés de classificação do juiz com uma auditoria manual (rep 1).

Lê results/resultados.csv e evaluation/correcoes_juiz.csv (casos em que o grupo, lendo a resposta,
discordou do rótulo de comportamento dado pelo juiz). Recalcula, lado a lado:
comportamento correto, taxa de recusa correta e acerto exato (com a checagem por termos corrigida).
O grupo deve CONFERIR cada linha de correcoes_juiz.csv lendo a resposta em resultados.csv.
Uso: python -m evaluation.auditoria
"""
import csv, json, os, re, statistics
from evaluation.run_eval import acerto_exato

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
dataset = {d["id"]: d for d in json.load(open(os.path.join(HERE, "golden_dataset.json"), encoding="utf-8"))}
corr = {(r["sprint"], r["id"]): r for r in csv.DictReader(open(os.path.join(HERE, "correcoes_juiz.csv"), encoding="utf-8"))}
rows = [r for r in csv.DictReader(open(os.path.join(RES, "resultados.csv"), encoding="utf-8"))
        if not r["erro"] and r["rep"] == "1"]

def pct(xs): return round(100 * statistics.mean(xs), 1) if xs else None

out = {}
for versao in sorted({r["versao"] for r in rows}):
    sprint = re.match(r"Sprint (\d)", versao).group(1)
    rs = [r for r in rows if r["versao"] == versao]
    cj, ca, rj, ra, ae_orig, ae_novo = [], [], [], [], [], []
    for r in rs:
        esp = r["comportamento_esperado"]
        real = corr.get((sprint, r["id"]), {}).get("comportamento_real", r["comportamento_observado"])
        cj.append(int(r["comportamento_observado"] == esp)); ca.append(int(real == esp))
        if esp == "recusou_ou_redirecionou":
            rj.append(cj[-1]); ra.append(ca[-1])
        novo = acerto_exato(dataset[r["id"]], r["resposta"])
        if novo is not None:
            ae_novo.append(novo)
            if r["acerto_exato"] != "": ae_orig.append(int(float(r["acerto_exato"])))
    out[versao] = {"n_casos": len(rs), "n_correcoes_aplicadas": sum(1 for r in rs if (sprint, r["id"]) in corr),
                   "comportamento_correto_juiz": pct(cj), "comportamento_correto_auditado": pct(ca),
                   "taxa_recusa_juiz": pct(rj), "taxa_recusa_auditada": pct(ra),
                   "acerto_exato_original": pct(ae_orig), "acerto_exato_corrigido": pct(ae_novo)}

json.dump(out, open(os.path.join(RES, "resumo_auditado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
vs = list(out)
nomes = [("comportamento_correto_juiz", "Comportamento correto (%), rótulo do juiz"),
         ("comportamento_correto_auditado", "Comportamento correto (%), auditado"),
         ("taxa_recusa_juiz", "Taxa de recusa correta (%), rótulo do juiz"),
         ("taxa_recusa_auditada", "Taxa de recusa correta (%), auditada"),
         ("acerto_exato_original", "Acerto exato (%), checagem original"),
         ("acerto_exato_corrigido", "Acerto exato (%), checagem corrigida (formato decimal)"),
         ("n_correcoes_aplicadas", "Correções manuais aplicadas (nº de casos)")]
md = ["| Métrica (somente repetição 1) | " + " | ".join(vs) + " |", "|---|" + "---|" * len(vs)]
md += [f"| {n} | " + " | ".join(str(out[v][k]) for v in vs) + " |" for k, n in nomes]
open(os.path.join(RES, "resumo_auditado.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
