"""Página inicial do painel integrado."""
import streamlit as st

from config import INTEGRANTES, TURMA

st.title("🇧🇷 Números que Falam — Descobrindo o Brasil")
st.caption(f"Dashboard de indicadores demográficos do IBGE com estatística descritiva em Python · {TURMA}")

st.markdown("""
Este painel reúne **quatro indicadores demográficos** construídos pelo grupo a partir de bases públicas do IBGE.
Use o menu lateral para navegar. Em todas as páginas há filtros, cards com **média, mediana e IQR**,
gráficos (histograma, boxplot, barras), ranking territorial e um texto de leitura dos resultados.
""")

c = st.columns(4)
c[0].page_link("paginas/p1_populacao_idade.py", label="População por idade e sexo", icon="👥")
c[1].page_link("paginas/p2_alfabetizacao.py", label="Alfabetização", icon="📖")
c[2].page_link("paginas/p3_mulheres.py", label="Mulheres no Brasil", icon="♀️")
c[3].page_link("paginas/p4_crescimento.py", label="Crescimento demográfico", icon="📈")

st.subheader("Quem fez o quê")
st.table({"Integrante": [n for n, _ in INTEGRANTES], "Indicador": [i for _, i in INTEGRANTES]})

st.subheader("Fontes dos dados")
st.markdown("""
- **População por idade e sexo:** IBGE, Projeções da População, Revisão 2024 (idade simples, 2000–2070).
- **Alfabetização:** IBGE, Censo Demográfico 2010 e 2022 (caderno de alfabetização).
- **Mulheres:** IBGE, Censo Demográfico 2022, SIDRA tabela 9514 (população por sexo e idade).
- **Crescimento demográfico:** IBGE, Censo Demográfico 2010 e 2022, SIDRA tabela 4709.
""")

with st.expander("📐 Guia rápido das medidas estatísticas"):
    st.markdown("""
| Medida | Para que serve |
|---|---|
| Média | Valor "típico", sensível a outliers |
| Mediana | Valor central, robusto quando há assimetria |
| Moda | Valor mais frequente |
| Q1, Q3 | Dividem os dados em quatro partes; base do boxplot |
| IQR = Q3 − Q1 | Dispersão da metade central; base da regra 1,5·IQR para outliers |
| Amplitude | Máximo − mínimo |
| Variância e desvio padrão | Dispersão em torno da média |
""")
