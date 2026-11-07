from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

import dados as D

st.set_page_config(page_title="Mulheres no Brasil | Números que Falam", page_icon="♀️", layout="wide")

BASE = Path(__file__).parent
COR_REG = {"Norte": "#2a9d8f", "Nordeste": "#e76f51", "Sudeste": "#264653", "Sul": "#8e6bbf",
           "Centro-Oeste": "#e9c46a", "—": "#999999"}
IND = {
    "pct_mulheres": ("% de mulheres na população", "%"),
    "razao_sexo": ("Razão de sexo (homens por 100 mulheres)", ""),
    "Mulheres": ("Nº de mulheres", ""),
    "pct_idosas": ("% de idosas (60+) entre as mulheres", "%"),
    "idade_med_f": ("Idade mediana das mulheres (anos)", ""),
}


def br(x, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(show_spinner="Lendo arquivo…")
def carregar_arquivo(nome, conteudo):
    return D.prepare(D.read_bytes(nome, conteudo))


@st.cache_data(ttl=86400, show_spinner="Baixando Censo 2022 (tabela 9514) do SIDRA…")
def carregar_api():
    return D.prepare(D.fetch_sidra())


st.sidebar.title("♀️ Mulheres no Brasil")
st.sidebar.caption("Startup *Números que Falam* · Projeto Integrador")
up = st.sidebar.file_uploader("📂 Upload de dados do IBGE (CSV/XLSX do SIDRA)", type=["csv", "xlsx", "xls"],
                              help="Exporte a tabela 9514 do SIDRA com Sexo e Idade em linhas e a coluna Valor.")
locais = sorted((BASE / "dados").glob("*.csv")) + sorted((BASE / "dados").glob("*.xlsx"))
try:
    if up is not None:
        tidy, fonte = carregar_arquivo(up.name, up.getvalue()), f"upload: {up.name}"
    elif locais:
        tidy, fonte = carregar_arquivo(locais[0].name, locais[0].read_bytes()), f"arquivo local: dados/{locais[0].name}"
    else:
        tidy, fonte = carregar_api(), "API do SIDRA · tabela 9514 (Censo 2022)"
except (requests.RequestException, ValueError, KeyError) as e:
    st.error(f"Não consegui carregar os dados: {e}")
    st.info("Baixe o CSV em https://sidra.ibge.gov.br/tabela/9514 (Território = UF; Sexo = Homens e Mulheres; "
            "Idade = grupos de 5 anos) e envie pelo botão de upload na barra lateral, "
            "ou salve o arquivo na pasta `dados/`.")
    st.stop()
st.sidebar.success(f"Fonte: {fonte}")

if tidy.empty:
    st.error("O arquivo foi lido, mas não encontrei linhas válidas de UF/Município com Homens e Mulheres.")
    st.stop()

st.sidebar.header("Filtros")
anos = sorted(tidy["ano"].unique())
ano = st.sidebar.selectbox("Ano", anos, index=len(anos) - 1) if len(anos) > 1 else anos[0]
t = tidy[tidy["ano"] == ano]

niveis = [n for n in ("UF", "Município") if n in t["nivel"].unique()]
nivel = st.sidebar.radio("Nível territorial", niveis, horizontal=True) if len(niveis) > 1 else niveis[0]

grupos = D.age_groups(t)
has_age = len(grupos) > 0
if has_age:
    g0, g1 = st.sidebar.select_slider("Faixa etária (recorte populacional)", options=grupos,
                                      value=(grupos[0], grupos[-1]))
    grupos_sel = grupos[grupos.index(g0): grupos.index(g1) + 1]
else:
    grupos_sel = []
    st.sidebar.caption("Arquivo sem faixas etárias: filtro de idade indisponível.")

base = D.build_base(t, grupos_sel, has_age)
base_nivel = base[base["nivel"] == nivel].copy()
regs = [r for r in D.REGIOES if r in base_nivel["regiao"].unique()]
reg_sel = st.sidebar.multiselect("Região", regs, default=regs)
ufs_disp = [u for u in D.UFS if D.UFS[u][1] in reg_sel and u in base_nivel["uf"].unique()]
uf_sel = st.sidebar.multiselect("UF", ufs_disp, default=ufs_disp, format_func=lambda u: f"{u} – {D.UFS[u][0]}")

opts = {k: v[0] for k, v in IND.items() if k in base_nivel and base_nivel[k].notna().any()}
ind = st.sidebar.selectbox("Indicador analisado", list(opts), format_func=opts.get)
ind_nome, ind_un = IND[ind]
topn = st.sidebar.slider("Municípios nos rankings (N maiores + N menores)", 5, 30, 10) if nivel == "Município" else None

df = base_nivel[base_nivel["uf"].isin(uf_sel)].dropna(subset=[ind]).copy()
if df.empty:
    st.warning("Nenhum território com os filtros atuais.")
    st.stop()
bench = {"pct": base_nivel["Mulheres"].sum() / base_nivel["Total"].sum() * 100,
         "razao": base_nivel["Homens"].sum() / base_nivel["Mulheres"].sum() * 100}
sel_pct = df["Mulheres"].sum() / df["Total"].sum() * 100
sel_razao = df["Homens"].sum() / df["Mulheres"].sum() * 100
S = D.describe(df[ind])
faixa_txt = f"{grupos_sel[0]} → {grupos_sel[-1]}" if has_age else "todas as idades"

st.title("♀️ Mulheres no Brasil: população feminina e comparações territoriais")
st.caption(f"Censo Demográfico 2022 · IBGE/SIDRA · ano {ano} · faixa etária: {faixa_txt} · nível: {nivel}")

with st.expander("🎯 Cenário e persona (leia antes de apresentar)", expanded=False):
    st.markdown(
        "**Quem pergunta:** *Fátima* (Secretária de Políticas para Mulheres de PE), *Maria* (Assistência Social da BA), "
        "*Luíza* (gestora do CE) e *Antônio* (gestor do AM) querem direcionar políticas para mulheres entre estados.\n\n"
        "**Nossa atuação (startup de dados):** mostramos **onde estão as mulheres**, quão **desiguais** são os territórios "
        "(média, mediana, IQR, desvio padrão) e quais **outliers** pedem atenção especial.")

c = st.columns(6)
c[0].metric("Mulheres (seleção)", br(df["Mulheres"].sum(), 0))
c[1].metric("% de mulheres", br(sel_pct) + "%", f"{sel_pct - bench['pct']:+.2f} p.p. vs. total do nível".replace(".", ","))
c[2].metric("Razão de sexo", br(sel_razao), "homens por 100 mulheres", delta_color="off")
c[3].metric(f"Média · {len(df)} territ.", br(S["Média"], 2))
c[4].metric("Mediana", br(S["Mediana"], 2))
c[5].metric("IQR", br(S["IQR"], 2), f"desvio padrão {br(S['Desvio padrão'], 2)}", delta_color="off")
st.caption(f"KPIs de média/mediana/IQR calculados sobre **{ind_nome}** entre os territórios filtrados.")

tabs = st.tabs(["📊 Comparação territorial", "📦 Distribuição e outliers", "🔺 Pirâmide etária",
                "🧮 Estatísticas", "💬 Perguntas de negócio", "📰 Notícias e imagens"])

with tabs[0]:
    ordem = df.sort_values(ind, ascending=False)
    plot = pd.concat([ordem.head(topn), ordem.tail(topn)]).drop_duplicates("territorio") if topn else ordem
    fig = px.bar(plot, x="territorio", y=ind, color="regiao", color_discrete_map=COR_REG,
                 labels={"territorio": "", ind: ind_nome, "regiao": "Região"}, text_auto=".2f",
                 title=f"{ind_nome} por território")
    ref = {"pct_mulheres": bench["pct"], "razao_sexo": bench["razao"]}.get(ind, df[ind].mean())
    fig.add_hline(y=ref, line_dash="dash", annotation_text="total do nível" if ind in ("pct_mulheres", "razao_sexo") else "média")
    fig.update_xaxes(categoryorder="array", categoryarray=plot["territorio"], tickangle=-45)
    if ind == "pct_mulheres":
        fig.update_yaxes(range=[max(0, plot[ind].min() - 1), plot[ind].max() + 0.6])
    st.plotly_chart(fig, width="stretch")

    g = plot.melt(id_vars=["territorio"], value_vars=["Mulheres", "Homens"], var_name="Sexo", value_name="Pessoas")
    fig2 = px.bar(g, x="territorio", y="Pessoas", color="Sexo", barmode="group",
                  color_discrete_map={"Mulheres": "#c2185b", "Homens": "#1f77b4"},
                  title="Mulheres × homens (nº de pessoas na faixa etária selecionada)", labels={"territorio": ""})
    fig2.update_xaxes(tickangle=-45)
    st.plotly_chart(fig2, width="stretch")

    if nivel == "UF" and st.checkbox("🗺️ Mostrar mapa coroplético por UF (baixa a malha do IBGE)"):
        try:
            gj = requests.get("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR",
                              params={"formato": "application/vnd.geo+json", "qualidade": "minima",
                                      "intrarregiao": "UF"}, timeout=40).json()
            m = df.copy()
            m["cod"] = m["uf"].map(lambda u: str(D.UFS[u][2]))
            fm = px.choropleth(m, geojson=gj, locations="cod", featureidkey="properties.codarea", color=ind,
                               hover_name="territorio", color_continuous_scale="RdPu", labels={ind: ind_nome})
            fm.update_geos(fitbounds="locations", visible=False)
            st.plotly_chart(fm, width="stretch")
        except Exception as e:
            st.warning(f"Não foi possível carregar o mapa agora: {e}")

    if "ano" in tidy and len(anos) > 1:
        ev = base[(base["nivel"] == nivel) & base["uf"].isin(uf_sel)].groupby(["ano", "regiao"], as_index=False)[
            ["Mulheres", "Total"]].sum()
        ev["pct"] = ev["Mulheres"] / ev["Total"] * 100
        st.plotly_chart(px.line(ev, x="ano", y="pct", color="regiao", markers=True, color_discrete_map=COR_REG,
                                title="Evolução do % de mulheres por região", labels={"pct": "% mulheres"}),
                        width="stretch")

with tabs[1]:
    box = pd.concat([df.assign(grupo="Seleção total"), df.assign(grupo=df["regiao"])])
    fb = px.box(box, x="grupo", y=ind, color="grupo", points="all", hover_name="territorio",
                color_discrete_map={**COR_REG, "Seleção total": "#555"}, labels={ind: ind_nome, "grupo": ""},
                title=f"Boxplot de {ind_nome}")
    fb.update_layout(showlegend=False)
    st.plotly_chart(fb, width="stretch")
    fh = px.histogram(df, x=ind, nbins=min(30, max(6, len(df) // 2)), labels={ind: ind_nome},
                      title="Histograma (linha sólida = média · tracejada = mediana)", color_discrete_sequence=["#c2185b"])
    fh.add_vline(x=S["Média"], line_color="black", annotation_text="média")
    fh.add_vline(x=S["Mediana"], line_color="green", line_dash="dash", annotation_text="mediana", annotation_position="bottom")
    st.plotly_chart(fh, width="stretch")
    out = df[(df[ind] < S["Limite inferior"]) | (df[ind] > S["Limite superior"])].sort_values(ind)
    st.subheader("Outliers (regra 1,5·IQR)")
    st.caption(f"Limites: {br(S['Limite inferior'], 2)} a {br(S['Limite superior'], 2)}")
    if out.empty:
        st.success("Nenhum outlier pela regra de Tukey nesta seleção.")
    else:
        st.dataframe(out[["territorio", "regiao", ind]].rename(columns={"territorio": "Território", "regiao": "Região", ind: ind_nome}),
                     hide_index=True, width="stretch")
    st.info(f"**Média × mediana:** média = {br(S['Média'], 2)} | mediana = {br(S['Mediana'], 2)} | "
            f"média sem outliers = {br(S['Média sem outliers'], 2)}. "
            + ("A diferença é pequena: a distribuição é quase simétrica." if abs(S["Média"] - S["Mediana"]) < 0.1 * (S["Desvio padrão"] or 1)
               else "Há assimetria: os extremos puxam a média; a mediana é a medida mais robusta."))

with tabs[2]:
    if not has_age:
        st.warning("O arquivo não tem faixas etárias; a pirâmide precisa da tabela 9514 por idade.")
    else:
        alvo = st.selectbox("Território", ["Consolidado da seleção"] + sorted(df["territorio"]))
        terr = df["territorio"] if alvo == "Consolidado da seleção" else [alvo]
        p = t[t["territorio"].isin(terr) & t["faixa"].isin(grupos) & t["sexo"].isin(["Homens", "Mulheres"])]
        p = p.groupby(["faixa", "sexo"], as_index=False)["valor"].sum()
        p["pct"] = p["valor"] / p["valor"].sum() * 100
        fp = go.Figure()
        for sx, cor, sg in (("Homens", "#1f77b4", -1), ("Mulheres", "#c2185b", 1)):
            q = p[p["sexo"] == sx].set_index("faixa").reindex(grupos)
            fp.add_bar(y=grupos, x=q["pct"] * sg, orientation="h", name=sx, marker_color=cor,
                       customdata=q["valor"], hovertemplate="%{y}<br>%{customdata:,.0f} pessoas<extra>" + sx + "</extra>")
        ticks = np.linspace(-10, 10, 9)
        fp.update_layout(barmode="relative", title=f"Pirâmide etária – {alvo}", xaxis_title="% da população",
                         xaxis=dict(tickvals=ticks, ticktext=[f"{abs(v):.1f}" for v in ticks]), height=560)
        st.plotly_chart(fp, width="stretch")
        r = t[t["territorio"].isin(terr) & t["faixa"].isin(grupos) & t["sexo"].isin(["Homens", "Mulheres"])]
        r = r.pivot_table(index="faixa", columns="sexo", values="valor", aggfunc="sum").reindex(grupos)
        r["razao"] = r["Homens"] / r["Mulheres"] * 100
        fr = px.line(r.reset_index(), x="faixa", y="razao", markers=True, title="Razão de sexo por faixa etária (homens por 100 mulheres)",
                     labels={"faixa": "", "razao": "Razão de sexo"})
        fr.add_hline(y=100, line_dash="dash", annotation_text="paridade")
        fr.update_xaxes(tickangle=-45)
        st.plotly_chart(fr, width="stretch")
        st.caption("Abaixo de 100, há mais mulheres que homens naquela faixa.")

with tabs[3]:
    st.subheader(f"Estatística descritiva – {ind_nome}")
    tab = {"Seleção total": S}
    for rg in [r for r in D.REGIOES if r in df["regiao"].unique()]:
        tab[rg] = D.describe(df.loc[df["regiao"] == rg, ind])
    est = pd.DataFrame(tab).T
    st.dataframe(est.style.format("{:,.3f}"), width="stretch")
    st.download_button("⬇️ Baixar tabela (CSV)", est.to_csv(sep=";", decimal=",").encode("utf-8-sig"), "estatisticas_mulheres.csv")
    st.markdown("**Como ler:** *IQR = Q3 − Q1* (dispersão da metade central); *amplitude = máx − mín*; "
                "*desvio padrão* mede o afastamento em torno da média; outliers = valores fora de "
                "[Q1 − 1,5·IQR ; Q3 + 1,5·IQR].")
    with st.expander("Dados tratados (base por território)"):
        st.dataframe(df.drop(columns=["ano"]), width="stretch", hide_index=True)
        st.download_button("⬇️ Baixar base tratada (CSV)", df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           "base_tratada.csv")

with tabs[4]:
    pm = df.sort_values("pct_mulheres", ascending=False)
    top, bot = pm.iloc[0], pm.iloc[-1]
    masc = pm[pm["razao_sexo"] > 100]
    st.markdown(f"""
#### 1) Onde as mulheres são mais (e menos) presentes?
Na seleção, as mulheres são **{br(sel_pct)}%** da população ({br(df['Mulheres'].sum(), 0)} pessoas; razão de sexo **{br(sel_razao)}**).
O maior percentual está em **{top['territorio']}** ({br(top['pct_mulheres'], 2)}%) e o menor em **{bot['territorio']}** ({br(bot['pct_mulheres'], 2)}%) –
amplitude de **{br(top['pct_mulheres'] - bot['pct_mulheres'], 2)} p.p.**
{"Territórios com mais homens que mulheres: **" + ", ".join(masc['territorio'].head(10)) + "**." if len(masc) else "Em nenhum território filtrado há maioria masculina."}

#### 2) Os territórios são homogêneos?
Para **{ind_nome}**: média **{br(S['Média'], 2)}**, mediana **{br(S['Mediana'], 2)}**, IQR **{br(S['IQR'], 2)}**,
desvio padrão **{br(S['Desvio padrão'], 2)}** (CV {br(S['Coef. variação (%)'], 1)}%). Há **{S['Nº outliers']} outlier(s)** pela regra 1,5·IQR
(veja a aba *Distribuição*). Com poucos outliers, média e mediana contam praticamente a mesma história.

#### 3) Como isso orienta as políticas?""")
    if "pct_idosas" in df and df["pct_idosas"].notna().any():
        ido = df.sort_values("pct_idosas", ascending=False).iloc[0]
        st.markdown(f"- **Envelhecimento feminino:** {ido['territorio']} tem a maior fatia de idosas (60+) entre as mulheres "
                    f"(**{br(ido['pct_idosas'], 1)}%**) → prioridade para saúde da mulher idosa, cuidado e previdência.")
    st.markdown(f"- **Territórios com maior razão de sexo** ({', '.join(df.sort_values('razao_sexo').tail(3)['territorio'])}) "
                "têm presença masculina maior (migração por trabalho, por exemplo): políticas de proteção e acesso devem considerar "
                "mulheres em menor proporção.\n"
                "- **Maior proporção de mulheres** ({}) → maior demanda absoluta por serviços voltados a elas.\n"
                "- **Histórico:** o Censo traz 1 ano; para ver evolução, envie as tabelas de 1991/2000/2010 do SIDRA no upload "
                "(o filtro *Ano* e o gráfico de evolução ativam automaticamente).".format(", ".join(pm.head(3)["territorio"])))

with tabs[5]:
    st.subheader("Notícias e contexto")
    imgs = sorted((BASE / "imagens").glob("*.png")) + sorted((BASE / "imagens").glob("*.jpg"))
    if imgs:
        cols = st.columns(len(imgs))
        for cc, im in zip(cols, imgs):
            cc.image(str(im), width="stretch")
        st.caption("Infográficos próprios feitos com dados divulgados pelo IBGE (Censo 2022).")
    NOT = [
        ("Censo 2022: para cada 100 mulheres, há cerca de 94 homens", "CNN Brasil",
         "https://www.cnnbrasil.com.br/nacional/censo-2022-para-cada-100-mulheres-ha-aproximadamente-94-homens-no-brasil/",
         "Resume o total de mulheres e homens e a razão de sexo nacional."),
        ("Mulheres são maioria em todas as regiões pela primeira vez", "Band Jornalismo / Agência Brasil",
         "https://www.band.com.br/noticias/censo-2022-mulheres-sao-maioria-em-todas-as-regioes-pela-primeira-vez-16643151",
         "Primeira vez em cinco décadas que o Norte também tem maioria feminina."),
        ("Brasil é feminino: mulheres são maioria em todas as regiões", "Forbes Mulher",
         "https://forbes.com.br/forbes-mulher/2023/10/brasil-e-feminino-mulheres-sao-maioria-em-todas-as-regioes-pela-primeira-vez/",
         "Mostra a proporção de mulheres nos estados e municípios."),
        ("Paraíba é o estado com maior percentual de mulheres", "Metrópoles",
         "https://www.metropoles.com/brasil/censo-2022-paraiba-e-o-estado-com-maior-percentual-de-mulheres",
         "Ranking estadual e municipal da presença feminina."),
        ("Idade mediana da população brasileira é de 35 anos", "CNN Brasil",
         "https://www.cnnbrasil.com.br/nacional/censo-2022-idade-mediana-da-populacao-brasileira-e-de-35-anos/",
         "Envelhecimento populacional e a maior proporção de mulheres."),
        ("Mulheres responsáveis por domicílios: de 38,7% a 49,1% em 10 anos", "Agência Gov / IBGE",
         "https://agenciagov.ebc.com.br/noticias/202410/censo-2022-em-12-anos-proporcao-de-mulheres-responsaveis-por-domicilios-avanca-e-se-equipara-a-de-homens",
         "Chefia feminina de lares, tema ligado ao indicador de rendimento."),
    ]
    for tt, fonte_n, url, desc in NOT:
        st.markdown(f"**[{tt}]({url})** · *{fonte_n}*  \n{desc}")
    st.markdown("---\nFonte dos dados: [SIDRA – tabela 9514](https://sidra.ibge.gov.br/tabela/9514) · "
                "[Agência de Notícias do IBGE](https://agenciadenoticias.ibge.gov.br/)")
