"""Painel integrado — Números que Falam. Executar:  streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="Números que Falam · IBGE", page_icon="🇧🇷", layout="wide")

paginas = [
    st.Page("paginas/inicio.py", title="Início", icon="🏠", default=True),
    st.Page("paginas/p1_populacao_idade.py", title="População por idade e sexo", icon="👥", url_path="populacao-idade"),
    st.Page("paginas/p2_alfabetizacao.py", title="Alfabetização", icon="📖", url_path="alfabetizacao"),
    st.Page("paginas/p3_mulheres.py", title="Mulheres no Brasil", icon="♀️", url_path="mulheres"),
    st.Page("paginas/p4_crescimento.py", title="Crescimento demográfico", icon="📈", url_path="crescimento"),
]
st.navigation(paginas).run()
