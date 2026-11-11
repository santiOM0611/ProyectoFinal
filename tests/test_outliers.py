import numpy as np
import pandas as pd

from modules.ai.outliers import detectar_outliers, outliers_iqr, outliers_zscore
from modules.type_detector import detectar_tipos


def test_zscore_e_iqr_marcan_el_valor_extremo():
    serie = pd.Series(list(np.random.default_rng(0).normal(10, 1, 200)) + [100.0])
    assert outliers_zscore(serie).iloc[-1]
    assert outliers_iqr(serie).iloc[-1]


def test_iqr_se_desactiva_si_mas_de_la_mitad_son_iguales():
    serie = pd.Series([1.0] * 50 + [2.0])
    assert not outliers_iqr(serie).any()


def test_detecta_el_outlier_plantado(df_mixto):
    esquema = detectar_tipos(df_mixto)
    res = detectar_outliers(df_mixto, esquema)
    marcas = res["datos_graficos"]["marcas"]
    assert marcas.loc[0, "es_outlier"]
    assert res["resumen"]["n_outliers"] <= 0.05 * len(df_mixto) + 1


def test_sin_columnas_numericas_se_omite():
    df = pd.DataFrame({"a": list("xyxyxyxyxy"), "b": list("pqpqpqpqpq")})
    res = detectar_outliers(df, detectar_tipos(df))
    assert res["omitido"]