"""Pequenos adaptadores para funcionar em versões diferentes do Streamlit
(width="stretch" nas versões novas; use_container_width nas antigas)."""
import inspect

import streamlit as st


def _chamar(func, *args, **kw):
    """Usa width="stretch" (Streamlit novo) e, se a versão instalada não aceitar, use_container_width=True."""
    try:
        if "width" in inspect.signature(func).parameters:
            return func(*args, width="stretch", **kw)
    except Exception:  # assinatura sem "width" ou valor não aceito nesta versão
        pass
    try:
        return func(*args, use_container_width=True, **kw)
    except TypeError:
        return func(*args, **kw)


def grafico(fig, **kw):
    return _chamar(st.plotly_chart, fig, **kw)


def tabela(df, **kw):
    return _chamar(st.dataframe, df, **kw)


def imagem(caminho, **kw):
    return _chamar(st.image, str(caminho), **kw)


def br(v, casas=0):
    """Número no padrão brasileiro (1.234,5)."""
    if v is None:
        return "–"
    try:
        if v != v:
            return "–"
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(v)
