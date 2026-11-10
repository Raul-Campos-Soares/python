"""Estatística descritiva usada pelas páginas (Pandas/NumPy).

Convenções (para a Profª Conceição validar):
- quartis: método linear do NumPy/Pandas (interpolação);
- desvio padrão e variância: AMOSTRAIS (n-1) nas séries de UFs/municípios; nas distribuições de idade
  (dados agrupados por idade simples, `resumo_ponderado`) usa-se n (população inteira);
- outlier: valor fora de [Q1 − 1,5·IQR ; Q3 + 1,5·IQR].
"""
import numpy as np
import pandas as pd


def br(v, casas=1):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resumo(serie):
    s = pd.Series(serie).dropna().astype(float)
    q1, med, q3 = s.quantile([.25, .5, .75])
    iqr = q3 - q1
    r1 = s.round(1)
    moda = None
    if len(r1) and r1.value_counts().iloc[0] > 1:
        moda = float(r1.mode().iloc[0])
    return {
        "n": int(len(s)), "media": float(s.mean()), "mediana": float(med), "moda": moda,
        "q1": float(q1), "q3": float(q3), "iqr": float(iqr), "minimo": float(s.min()), "maximo": float(s.max()),
        "amplitude": float(s.max() - s.min()), "variancia": float(s.var()), "desvio_padrao": float(s.std()),
        "lim_inf": float(q1 - 1.5 * iqr), "lim_sup": float(q3 + 1.5 * iqr),
    }


def outliers(df, col, rotulo):
    """Linhas fora dos limites de 1,5·IQR; devolve só [rotulo, col], ordenado por col."""
    r = resumo(df[col])
    fora = df[(df[col] < r["lim_inf"]) | (df[col] > r["lim_sup"])]
    return fora[[rotulo, col]].sort_values(col)


def interpretar_taxa(r, unidade="UFs"):
    """Texto de leitura (média x mediana, dispersão) para uma taxa em %."""
    dif = r["media"] - r["mediana"]
    if abs(dif) < 0.1 * (r["desvio_padrao"] or 1):
        lado = (f"Média ({br(r['media'], 2)}%) e mediana ({br(r['mediana'], 2)}%) são praticamente iguais: "
                "a distribuição é aproximadamente simétrica e qualquer das duas resume bem o conjunto.")
    elif dif < 0:
        lado = (f"A média ({br(r['media'], 2)}%) fica abaixo da mediana ({br(r['mediana'], 2)}%): "
                f"poucas {unidade} com valores baixos puxam a média para baixo (assimetria à esquerda). "
                "A mediana é a referência mais robusta.")
    else:
        lado = (f"A média ({br(r['media'], 2)}%) fica acima da mediana ({br(r['mediana'], 2)}%): "
                f"poucas {unidade} com valores altos puxam a média para cima (assimetria à direita). "
                "A mediana é a referência mais robusta.")
    disp = (f" A metade central das {unidade} está entre {br(r['q1'], 1)}% e {br(r['q3'], 1)}% "
            f"(IQR = {br(r['iqr'], 2)} p.p.); a amplitude é de {br(r['amplitude'], 1)} p.p. e o desvio padrão, "
            f"{br(r['desvio_padrao'], 2)} p.p.")
    return lado + disp


def resumo_ponderado(valores, pesos):
    """Estatísticas de uma distribuição de frequências (ex.: idade simples x população).

    Quantis discretos: menor valor cuja frequência acumulada atinge p. Variância populacional (n).
    """
    x = np.asarray(valores, dtype=float)
    w = np.asarray(pesos, dtype=float)
    w = np.where(np.isfinite(w), w, 0.0)
    tot = w.sum()
    if tot <= 0:
        return None
    media = float((x * w).sum() / tot)
    var = float((w * (x - media) ** 2).sum() / tot)
    cum = np.cumsum(w) / tot

    def q(p):
        return float(x[min(int(np.searchsorted(cum, p - 1e-12)), len(x) - 1)])

    q1, med, q3 = q(.25), q(.5), q(.75)
    iqr = q3 - q1
    return {"total": float(tot), "media": media, "mediana": med, "moda": float(x[int(np.argmax(w))]),
            "q1": q1, "q3": q3, "iqr": iqr, "amplitude": float(x.max() - x.min()),
            "variancia": var, "desvio_padrao": var ** 0.5,
            "lim_inf": q1 - 1.5 * iqr, "lim_sup": q3 + 1.5 * iqr}
