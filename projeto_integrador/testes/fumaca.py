"""Teste de fumaça: executa cada página com Streamlit/Plotly SIMULADOS (não há essas bibliotecas no ambiente de
desenvolvimento). Valida que o código roda, que as colunas usadas nos gráficos existem e que x/y têm o mesmo tamanho.
Não valida a aparência: isso só rodando `streamlit run app.py`."""
import functools, runpy, sys, types
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
LOG = {"error": [], "warning": [], "calls": 0, "plots": 0, "colunas_ok": 0}
OVR = {}          # sobrescreve valores de widgets: {trecho do rótulo: valor}


class Stop(Exception):
    pass


def _ovr(label, default):
    return OVR.get(str(label), default)


class Api:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, nome):
        def f(*a, **k):
            LOG["calls"] += 1
            if nome in ("error", "warning"):
                LOG[nome].append(str(a[0])[:150])
            return None
        return f
    # --- widgets com retorno
    def selectbox(self, label, options, index=0, format_func=str, **k):
        options = list(options)
        for o in options: format_func(o)
        v = _ovr(label, None)
        return v if v is not None else (options[index] if options else None)
    def radio(self, label, options, index=0, format_func=str, **k):
        options = list(options)
        for o in options: format_func(o)
        v = _ovr(label, None)
        return v if v is not None else options[index]
    def multiselect(self, label, options, default=None, format_func=str, **k):
        options = list(options)
        for o in options: format_func(o)
        v = _ovr(label, None)
        r = v if v is not None else (list(default) if default is not None else [])
        assert all(x in options for x in r), f"multiselect '{label}': default fora das opções {r}"
        return r
    def slider(self, label, min_value=None, max_value=None, value=None, *a, **k):
        v = _ovr(label, None)
        if v is not None: return v
        if value is not None: return value
        return min_value
    def select_slider(self, label, options=(), value=None, **k):
        return value if value is not None else list(options)[0]
    def checkbox(self, label, value=False, **k): return _ovr(label, value)
    def file_uploader(self, *a, **k): return None
    def button(self, *a, **k): return False
    def text_input(self, label, value="", **k): return value
    def columns(self, spec, **k):
        return [Api() for _ in range(spec if isinstance(spec, int) else len(spec))]
    def tabs(self, nomes): return [Api() for _ in nomes]
    def expander(self, *a, **k): return Api()
    def spinner(self, *a, **k): return Api()
    def stop(self): raise Stop()


def montar_streamlit():
    st = types.ModuleType("streamlit")
    api = Api(); st.sidebar = Api()
    def cache_data(func=None, **kw):
        if func is None: return lambda f: functools.lru_cache(maxsize=None)(f) if False else f
        return func
    st.cache_data = cache_data
    st.cache_resource = cache_data
    st.Page = lambda *a, **k: ("page", a)
    st.navigation = lambda p: Api()
    st.stop = api.stop
    def __getattr__(nome): return getattr(api, nome)
    st.__getattr__ = __getattr__
    return st


# ------------------------------------------------------------------ plotly simulado
class Fig:
    def __getattr__(self, nome):
        return lambda *a, **k: self


ARG_COLUNA = ("x", "y", "color", "text", "hover_name", "size", "facet_col", "locations")


def _checa(nome, df, kw):
    LOG["plots"] += 1
    if not isinstance(df, pd.DataFrame): return
    for a in ARG_COLUNA:
        v = kw.get(a)
        if isinstance(v, str):
            assert v in df.columns, f"px.{nome}: coluna '{v}' ({a}) não existe em {list(df.columns)}"
            LOG["colunas_ok"] += 1
    for h in (kw.get("hover_data") or []):
        if isinstance(h, str):
            assert h in df.columns, f"px.{nome}: hover_data '{h}' inexistente"
    if kw.get("y") is not None and len(df) == 0:
        pass


def _px(nome):
    def f(df=None, *a, **kw):
        _checa(nome, df, kw)
        return Fig()
    return f


def _trace(nome):
    def f(*a, **kw):
        LOG["plots"] += 1
        x, y = kw.get("x"), kw.get("y")
        if x is not None and y is not None and not isinstance(x, str) and not isinstance(y, str):
            assert len(x) == len(y), f"go.{nome}: x ({len(x)}) e y ({len(y)}) com tamanhos diferentes"
        return Fig()
    return f


def instalar(extra=None):
    sys.modules["streamlit"] = montar_streamlit()
    px = types.ModuleType("plotly.express")
    for n in ("bar", "box", "histogram", "line", "scatter", "choropleth", "area", "violin"):
        setattr(px, n, _px(n))
    go = types.ModuleType("plotly.graph_objects")
    go.Figure = lambda *a, **k: Fig()
    for n in ("Bar", "Box", "Scatter", "Histogram"):
        setattr(go, n, _trace(n))
    pl = types.ModuleType("plotly"); pl.express, pl.graph_objects = px, go
    sys.modules.update({"plotly": pl, "plotly.express": px, "plotly.graph_objects": go})
    for m in ("ui",):
        sys.modules.pop(m, None)


def rodar(pagina, **ovr):
    OVR.clear(); OVR.update(ovr)
    for k in ("error", "warning"): LOG[k].clear()
    LOG["plots"] = LOG["calls"] = 0
    try:
        runpy.run_path(str(RAIZ / "paginas" / pagina), run_name="__main__")
        estado = "ok"
    except Stop:
        estado = "STOP"
    return estado
