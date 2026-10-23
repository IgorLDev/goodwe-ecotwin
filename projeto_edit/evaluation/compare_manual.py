"""
compare_manual.py — confronta o pipeline automatizado com a avaliação manual da Sprint 3.

Pré-requisito: preencher evaluation/avaliacao_manual_sprint3.csv com o veredito
que o grupo deu na Sprint 3 (OK / PARCIAL / FALHOU) para cada caso, com base nas
anotações, logs/security_test_results.jsonl e leitura manual. NÃO preencher "de cabeça".

Veredito do pipeline por caso (média das repetições): OK se nota_final >= 80 e
comportamento_correto >= 0.5; caso contrário, FALHOU. PARCIAL manual conta como não-OK.
Uso: python -m evaluation.compare_manual [--versao "Sprint 3 (gpt-4o-mini)"]
"""
import argparse, csv, json, os, statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versao", default="Sprint 3 (gpt-4o-mini)")
    args = ap.parse_args()

    manual = {r["id"]: r for r in csv.DictReader(open(os.path.join(HERE, "avaliacao_manual_sprint3.csv"), encoding="utf-8"))
              if r["veredito_manual"].strip()}
    if not manual:
        raise SystemExit("Preencha a coluna veredito_manual em avaliacao_manual_sprint3.csv antes de rodar.")
    linhas = [r for r in csv.DictReader(open(os.path.join(RES, "resultados.csv"), encoding="utf-8"))
              if r["versao"] == args.versao and not r["erro"]]
    por_caso = defaultdict(list)
    for r in linhas:
        por_caso[r["id"]].append(r)

    itens, a, b = [], [], []
    for cid, m in manual.items():
        if cid not in por_caso:
            continue
        rs = por_caso[cid]
        nota = statistics.mean(float(r["nota_final"]) for r in rs)
        comp = statistics.mean(float(r["comportamento_correto"]) for r in rs)
        pipe_ok = int(nota >= 80 and comp >= 0.5)
        man_ok = int(m["veredito_manual"].strip().upper() == "OK")
        a.append(man_ok); b.append(pipe_ok)
        itens.append({"id": cid, "manual": m["veredito_manual"].strip().upper(), "pipeline": "OK" if pipe_ok else "FALHOU",
                      "nota_pipeline": round(nota, 1), "concorda": man_ok == pipe_ok,
                      "obs_manual": m["observacao"], "justificativa_juiz": rs[0]["justificativa"]})
    out = {"versao": args.versao, "n": len(itens),
           "concordancia_pct": round(100 * sum(x == y for x, y in zip(a, b)) / len(itens), 1),
           "kappa_cohen": kappa(a, b), "itens": itens}
    json.dump(out, open(os.path.join(RES, "comparacao_manual.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Concordância: {out['concordancia_pct']}% em {out['n']} casos | kappa = {out['kappa_cohen']}")
    for i in itens:
        if not i["concorda"]:
            print(f"DIVERGE {i['id']}: manual={i['manual']} pipeline={i['pipeline']} ({i['nota_pipeline']}) — {i['justificativa_juiz']}")


if __name__ == "__main__":
    main()
