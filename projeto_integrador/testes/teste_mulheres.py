"""Teste com dados SINTÉTICOS no formato da API do SIDRA (não são dados do IBGE): valida o código, não os números."""
import sys, random
sys.path.insert(0, "..")
import numpy as np, pandas as pd
import dados_mulheres as D
from geo import UFS

random.seed(1)
cab = {"NC": "Nível Territorial (Código)", "NN": "Nível Territorial", "MC": "Unidade de Medida (Código)",
       "MN": "Unidade de Medida", "V": "Valor", "D1C": "Unidade da Federação (Código)", "D1N": "Unidade da Federação",
       "D2C": "Variável (Código)", "D2N": "Variável", "D3C": "Ano (Código)", "D3N": "Ano", "D4C": "Sexo (Código)",
       "D4N": "Sexo", "D5C": "Forma de declaração da idade (Código)", "D5N": "Forma de declaração da idade",
       "D6C": "Idade (Código)", "D6N": "Idade"}

def gerar(modo):
    rows = [cab]
    for s, (nome, reg, cod) in UFS.items():
        base = random.randint(1_000_000, 9_000_000)
        for sexo in ("Homens", "Mulheres"):
            if modo == "grupos":
                rotulos = [f"{a} a {a+4} anos" for a in range(0, 100, 5)] + ["100 anos ou mais"]
            else:
                rotulos = ["Menos de 1 ano"] + [f"{a} anos" if a != 1 else "1 ano" for a in range(1, 100)] + ["100 anos ou mais"]
            for r in rotulos:
                for forma in ("Total", "Data de nascimento"):
                    v = random.randint(1000, 90000) * (1.05 if sexo == "Mulheres" else 1)
                    rows.append({"NC": "3", "NN": "Unidade da Federação", "MC": "45", "MN": "Pessoas", "V": str(int(v)),
                                 "D1C": str(cod), "D1N": nome, "D2C": "93", "D2N": "População residente", "D3C": "2022",
                                 "D3N": "2022", "D4C": "4", "D4N": sexo, "D5C": "1", "D5N": forma, "D6C": "1", "D6N": r})
        # linhas "Total" que não podem ser contadas em dobro
        rows.append({"NC": "3", "NN": "UF", "MC": "45", "MN": "Pessoas", "V": "5000000", "D1C": str(cod), "D1N": nome,
                     "D2C": "93", "D2N": "População residente", "D3C": "2022", "D3N": "2022", "D4C": "6794",
                     "D4N": "Total", "D5C": "1", "D5N": "Total", "D6C": "1", "D6N": "Total"})
    return rows

for modo in ("grupos", "simples"):
    raw = D._api_para_raw(gerar(modo))
    t = D.prepare(raw)
    g = D.age_groups(t)
    print(modo, "| linhas raw", len(raw), "| tidy", len(t), "| grupos", len(g), g[0], g[-1])
    assert len(g) == 21 and g[-1] == "100 anos ou mais" and "Total" not in g
    b = D.build_base(t, g, True)
    assert len(b) == 27 and b["pct_mulheres"].between(30, 70).all()
    assert {"pct_idosas", "idade_med_f"} <= set(b.columns)
    print(b[["territorio", "Mulheres", "pct_mulheres", "razao_sexo", "pct_idosas", "idade_med_f"]].head(3).round(2))
    b2 = D.build_base(t, g[:10], True); assert (b2["Total"] < b["Total"]).all()
    d = D.describe(b["pct_mulheres"]); assert d["n"] == 27
    # round-trip CSV canônico
    csv = raw.to_csv(index=False).encode()
    t2 = D.prepare(D.read_bytes("x.csv", csv)); assert len(t2) == len(t)
# sem idade
sem = pd.DataFrame({"territorio": ["Acre", "Acre"], "sexo": ["Homens", "Mulheres"], "valor": ["400000", "430000"]})
ts = D.prepare(D._raw_de_tabela(sem)); bs = D.build_base(ts, [], False)
print(bs[["territorio", "Total", "pct_mulheres"]]); assert "pct_idosas" not in bs
# município
mun = pd.DataFrame({"territorio": ["Santa Luzia (MG)", "Santa Luzia - MG"], "sexo": ["Homens", "Mulheres"],
                    "idade": ["Total", "Total"], "ano": [2022, 2022], "valor": ["100", "110"]})
tm = D.prepare(mun); print(tm[["nivel", "territorio", "uf", "regiao"]])
print("TESTE MULHERES OK")
