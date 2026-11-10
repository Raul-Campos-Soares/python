"""Baixa a tabela 9514 do SIDRA/IBGE (Censo 2022: população por sexo e idade, por UF) e salva em dados/.

Uso:   python baixar_dados_mulheres.py
Depois disso o painel funciona sem internet.
"""
from pathlib import Path

import dados_mulheres as D

destino = Path(__file__).parent / "dados" / "censo2022_sexo_idade_uf.csv"
print("Baixando da API do IBGE (pode levar alguns segundos)...")
raw = D.fetch_sidra()
D.prepare(raw)  # valida: se algo estiver errado, falha aqui
destino.parent.mkdir(exist_ok=True)
raw.to_csv(destino, index=False, encoding="utf-8")
print(f"OK: {len(raw)} linhas salvas em {destino}")
