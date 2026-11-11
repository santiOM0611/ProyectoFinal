import numpy as np
import pandas as pd

from modules.ai.clustering import agrupar, estimar_eps
from modules.type_detector import detectar_tipos


def test_encuentra_dos_grupos(df_mixto):
    df = df_mixto.iloc[1:].reset_index(drop=True)       # sin el outlier
    res = agrupar(df, detectar_tipos(df))
    assert not res["omitido"]
    assert res["resumen"]["kmeans_k"] == 2
    assert res["resumen"]["kmeans_silhouette"] > 0.5


def test_excluir_columnas(df_mixto):
    df = df_mixto.iloc[1:].reset_index(drop=True)
    res = agrupar(df, detectar_tipos(df), excluir=("edad", "ruido"))
    assert res["omitido"]            # queda 1 sola columna


def test_datos_discretos_generan_aviso():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.integers(0, 3, 500), "b": rng.integers(0, 3, 500)})
    res = agrupar(df, detectar_tipos(df))
    assert res["resumen"]["datos_discretos"]
    assert any("combinaciones" in a for a in res["advertencias"])


def test_eps_nunca_es_cero_con_puntos_repetidos():
    X = np.zeros((100, 2))
    X[:3] = [[1, 1], [2, 2], [3, 3]]
    assert estimar_eps(X, 5) > 0


def test_las_etiquetas_cubren_todas_las_filas(df_mixto):
    res = agrupar(df_mixto, detectar_tipos(df_mixto))
    assert len(res["tablas"]["etiquetas"]) == len(df_mixto)


def test_con_muchas_filas_usa_muestra_y_etiqueta_todas(monkeypatch):
    from modules import config
    monkeypatch.setattr(config, "MAX_FILAS_BUSQUEDA", 400)
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": np.r_[rng.normal(0, 1, 500), rng.normal(8, 1, 500)],
                       "b": np.r_[rng.normal(0, 1, 500), rng.normal(8, 1, 500)]})
    res = agrupar(df, detectar_tipos(df))
    assert res["resumen"]["kmeans_k"] == 2
    assert len(res["tablas"]["etiquetas"]) == 1000
    assert any("muestra" in a for a in res["advertencias"])
    