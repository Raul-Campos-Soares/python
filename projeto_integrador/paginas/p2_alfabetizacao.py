"""Página 2 — Alfabetização por sexo, UF e ano (Censo Demográfico 2010 e 2022, IBGE)."""
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from estatistica import interpretar_taxa, outliers, resumo
from etl_alfabetizacao import REGIOES, carregar_base, evolucao_uf, nivel

AZUL, LARANJA, VERDE = "#2A5FA5", "#D9772B", "#2F7D5B"
COR_SEXO = {"Homens": AZUL, "Mulheres": LARANJA, "Total": "#6B7280"}
ARQ_PADRAO = Path(__file__).resolve().parent.parent / "dados" / "alfabetizacao_ibge_censo2022.csv"


def fmt(n, dec=1):
    return f"{n:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------ Dados e filtros
st.sidebar.title("📂 Dados")
up = st.sidebar.file_uploader("Base de alfabetização (CSV/XLSX)", type=["csv", "xlsx"],
                              help="Colunas: Nivel, Territorio, UF, Regiao, Ano, Sexo, Faixa_Etaria, Taxa_Alfabetizacao. "
                                   "Se a base trouxer Homens/Mulheres por UF, o painel mostra a diferença por UF.")
try:
    df = carregar_base(up if up is not None else ARQ_PADRAO)
except Exception as e:
    st.error(f"Não foi possível ler a base: {e}")
    st.stop()

anos = sorted(df["Ano"].unique())
st.sidebar.title("🔎 Filtros")
ano = st.sidebar.selectbox("Ano", anos, index=len(anos) - 1)
regs = [r for r in REGIOES if r in set(df["Regiao"])]
sel_reg = st.sidebar.multiselect("Região", regs, default=regs)
ufs_all = nivel(df, "UF")
ufs_opc = sorted(ufs_all[ufs_all["Regiao"].isin(sel_reg)]["UF"].unique())
sel_uf = st.sidebar.multiselect("UF", ufs_opc, default=ufs_opc)
sexos = sorted(set(df["Sexo"]) - {"Total"})
sel_sexo = st.sidebar.multiselect("Sexo", sexos, default=sexos)

uf_f = ufs_all[ufs_all["UF"].isin(sel_uf)]
uf_ano = uf_f[uf_f["Ano"] == ano]

# ------------------------------------------------------------------ Cabeçalho + KPIs
st.title("Alfabetização no Brasil: sexo, território e tempo")
st.caption("Taxa de alfabetização das pessoas de 15 anos ou mais · Censo Demográfico 2010 e 2022 · IBGE")

br = nivel(df, "Brasil")


def br_val(a, sexo="Total", faixa="15+"):
    s = df[(df["Nivel"] == "Brasil") & (df["Ano"] == a) & (df["Sexo"] == sexo) & (df["Faixa_Etaria"] == faixa)]
    return float(s["Taxa_Alfabetizacao"].iloc[0]) if len(s) else None


tot, tot0 = br_val(ano), br_val(anos[0])
h, m = br_val(ano, "Homens"), br_val(ano, "Mulheres")
k = st.columns(4)
k[0].metric(f"Brasil · {ano}", f"{fmt(tot)}%", f"{fmt(tot - tot0)} p.p. vs {anos[0]}" if tot and tot0 and ano != anos[0] else None)
k[1].metric("Mulheres", f"{fmt(m)}%" if m else "—")
k[2].metric("Homens", f"{fmt(h)}%" if h else "—")
k[3].metric("Diferença (M − H)", f"{fmt(m - h)} p.p." if m and h else "—")

aba1, aba2, aba3, aba4, aba5 = st.tabs(["⚖️ Por sexo", "🗺️ Por UF", "📈 Evolução", "📐 Estatística", "📰 Contexto"])

# ------------------------------------------------------------------ Por sexo
with aba1:
    sx = df[(df["Nivel"] == "Brasil") & (df["Ano"] == ano) & (df["Sexo"].isin(sel_sexo))]
    if sx.empty:
        st.info(f"A base não tem dados por sexo para {ano}. No arquivo padrão, o recorte por sexo existe só para 2022.")
    else:
        fig = px.bar(sx, x="Faixa_Etaria", y="Taxa_Alfabetizacao", color="Sexo", barmode="group",
                     text="Taxa_Alfabetizacao", color_discrete_map=COR_SEXO,
                     labels={"Faixa_Etaria": "Faixa etária", "Taxa_Alfabetizacao": "Taxa de alfabetização (%)"},
                     title=f"Alfabetização por sexo — Brasil, {ano}")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_yaxes(range=[60, 100])
        ui.grafico(fig)
        st.caption("Eixo iniciando em 60% para tornar visíveis diferenças de poucos pontos percentuais.")
        st.markdown(
            "Entre todos os adultos, as mulheres têm taxa ligeiramente maior que os homens. "
            "No grupo de 65 anos ou mais a diferença some e as taxas ficam em torno de 80%, "
            "ou seja, o gargalo hoje é **idade e território**, mais que sexo.")

    com_sexo_uf = (not ufs_all.empty) and df[(df["Nivel"] == "UF") & df["Sexo"].isin(["Homens", "Mulheres"])].shape[0] > 0
    if com_sexo_uf:
        s = df[(df["Nivel"] == "UF") & (df["Ano"] == ano) & df["Sexo"].isin(["Homens", "Mulheres"]) & df["UF"].isin(sel_uf)]
        p = s.pivot_table(index="UF", columns="Sexo", values="Taxa_Alfabetizacao").reset_index()
        p["Diferenca_pp"] = p["Mulheres"] - p["Homens"]
        fig = px.bar(p.sort_values("Diferenca_pp"), x="UF", y="Diferenca_pp", color_discrete_sequence=[LARANJA],
                     title="Diferença Mulheres − Homens por UF (p.p.)")
        ui.grafico(fig)
    else:
        st.caption("O recorte sexo × UF não está no arquivo padrão. Exporte-o do SIDRA e envie pela barra lateral para ativar a diferença por UF.")

# ------------------------------------------------------------------ Por UF
with aba2:
    if uf_ano.empty:
        st.warning("Nenhuma UF selecionada.")
    else:
        d = uf_ano.sort_values("Taxa_Alfabetizacao")
        fig = px.bar(d, x="Taxa_Alfabetizacao", y="UF", orientation="h", color="Regiao",
                     text="Taxa_Alfabetizacao", labels={"Taxa_Alfabetizacao": "Taxa (%)"},
                     title=f"Taxa de alfabetização por UF — {ano}",
                     color_discrete_sequence=[AZUL, LARANJA, VERDE, "#8B5E9B", "#B0903C"])
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_xaxes(range=[60, 102])
        fig.update_layout(height=max(420, 22 * len(d)), yaxis_title=None)
        ui.grafico(fig)

        rg = nivel(df, "Região")
        rg = rg[rg["Regiao"].isin(sel_reg)]
        fig = px.bar(rg, x="Regiao", y="Taxa_Alfabetizacao", color=rg["Ano"].astype(str), barmode="group",
                     text="Taxa_Alfabetizacao", title="Taxa por Grande Região",
                     labels={"Taxa_Alfabetizacao": "Taxa (%)", "color": "Ano", "Regiao": "Região"},
                     color_discrete_sequence=["#9CA3AF", AZUL])
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_yaxes(range=[60, 102])
        ui.grafico(fig)

# ------------------------------------------------------------------ Evolução
with aba3:
    ev = evolucao_uf(df)
    ev = ev[ev["UF"].isin(sel_uf)] if not ev.empty else ev
    if ev.empty or "Ganho_pp" not in ev:
        st.info("A base tem apenas um ano; a evolução precisa de ao menos dois.")
    else:
        fig = px.bar(ev.sort_values("Ganho_pp", ascending=False), x="UF", y="Ganho_pp", color="Regiao",
                     title=f"Ganho na taxa de alfabetização, {anos[0]}→{anos[-1]} (p.p.)",
                     labels={"Ganho_pp": "Ganho (p.p.)"},
                     color_discrete_sequence=[AZUL, LARANJA, VERDE, "#8B5E9B", "#B0903C"])
        ui.grafico(fig)
        melhor = ev.sort_values("Ganho_pp", ascending=False).iloc[0]
        st.markdown(f"Maior avanço: **{melhor['Territorio']}** (+{fmt(melhor['Ganho_pp'])} p.p.). "
                    "Os estados com menor taxa inicial foram os que mais ganharam, o que indica **convergência** entre UFs.")
        ui.tabela(ev.rename(columns={"Territorio": "UF (nome)", "Regiao": "Região", "Ganho_pp": "Ganho (p.p.)"})
                     .sort_values("Ganho (p.p.)", ascending=False), hide_index=True)

# ------------------------------------------------------------------ Estatística
with aba4:
    st.subheader(f"Estatística descritiva entre UFs — {ano}")
    if len(uf_ano) < 4:
        st.warning("Selecione ao menos 4 UFs para quartis e outliers fazerem sentido.")
    else:
        r = resumo(uf_ano["Taxa_Alfabetizacao"])
        a = st.columns(4)
        a[0].metric("Média", f"{fmt(r['media'], 2)}%")
        a[1].metric("Mediana", f"{fmt(r['mediana'], 2)}%")
        a[2].metric("IQR (Q3−Q1)", f"{fmt(r['iqr'], 2)} p.p.")
        a[3].metric("Desvio padrão", f"{fmt(r['desvio_padrao'], 2)} p.p.")
        b = st.columns(4)
        b[0].metric("Q1", f"{fmt(r['q1'], 2)}%")
        b[1].metric("Q3", f"{fmt(r['q3'], 2)}%")
        b[2].metric("Amplitude", f"{fmt(r['amplitude'], 2)} p.p.")
        b[3].metric("Moda", f"{fmt(r['moda'], 1)}%" if r["moda"] else "sem repetição")
        st.caption(f"Variância: {fmt(r['variancia'], 2)} · n = {r['n']} UFs · "
                   f"limites de outlier (1,5×IQR): [{fmt(r['lim_inf'], 1)} ; {fmt(r['lim_sup'], 1)}]")

        fig = go.Figure()
        for a_, cor in zip(anos, ["#9CA3AF", AZUL]):
            x = uf_f[uf_f["Ano"] == a_]
            fig.add_trace(go.Box(x=x["Taxa_Alfabetizacao"], text=x["UF"], name=str(a_), boxpoints="all",
                                 jitter=.5, boxmean=True, marker_color=cor, orientation="h"))
        fig.update_layout(title="Boxplot das taxas por UF (◆ = média)", xaxis_title="Taxa de alfabetização (%)",
                          height=360)
        ui.grafico(fig)

        out = outliers(uf_ano, "Taxa_Alfabetizacao", "UF")
        if out.empty:
            menor = uf_ano.sort_values("Taxa_Alfabetizacao").iloc[0]
            st.success(f"Nenhum outlier pela regra 1,5×IQR. A menor taxa ({menor['UF']}, "
                       f"{fmt(menor['Taxa_Alfabetizacao'])}%) está abaixo do grupo, mas dentro do limite inferior.")
        else:
            st.warning("Outliers (1,5×IQR): " + ", ".join(f"{u} ({fmt(t)}%)" for u, t in out.values))
        st.markdown("**Interpretação:** " + interpretar_taxa(r, "UFs"))

        if len(anos) >= 2:
            r0 = resumo(uf_f[uf_f["Ano"] == anos[0]]["Taxa_Alfabetizacao"])
            st.markdown(f"**{anos[0]} → {ano}:** mediana {fmt(r0['mediana'])}% → {fmt(r['mediana'])}%; "
                        f"IQR {fmt(r0['iqr'])} → {fmt(r['iqr'])} p.p.; desvio padrão {fmt(r0['desvio_padrao'])} → "
                        f"{fmt(r['desvio_padrao'])} p.p. A dispersão caiu: as UFs ficaram mais parecidas.")
        st.caption("Estatísticas calculadas sobre as taxas das UFs, sem ponderar pela população de cada uma.")

# ------------------------------------------------------------------ Contexto
with aba5:
    st.subheader("Perguntas para a roda de conversa")
    st.markdown("""
- **Quem ainda fica para trás?** As UFs do Nordeste (Alagoas, Piauí, Paraíba, Maranhão) seguem abaixo de 86%.
- **Existe desigualdade por sexo?** Em 2022, as mulheres têm taxa um pouco maior no total, mas a vantagem some entre idosos.
- **A distância entre estados diminuiu?** Sim: amplitude, IQR e desvio padrão caíram de 2010 para 2022.
- **Mediana ou média?** A mediana, porque poucas UFs com taxas baixas puxam a média para baixo.
""")
    st.subheader("Fontes e notícias")
    st.markdown("""
- [IBGE — Censo Demográfico 2022](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827)
- [IBGE — caderno de alfabetização, Censo 2022 (PDF)](https://biblioteca.ibge.gov.br/visualizacao/periodicos/3108/cd_2022_alfabetizacao.pdf)
- [Correio Braziliense — alfabetizados no país são 93%](https://www.correiobraziliense.com.br/brasil/2024/05/6859829-alfabetizados-no-pais-sao-93-mostra-censo.html)
- [Poder360 — 11,4 milhões não sabem ler e escrever](https://www.poder360.com.br/brasil/114-milhoes-de-brasileiros-nao-sabem-ler-e-escrever-bilhete-simples/)
""")
    st.caption("Fonte dos dados: IBGE, Censo Demográfico 2010 e 2022 (tabelas publicadas no caderno de alfabetização).")
