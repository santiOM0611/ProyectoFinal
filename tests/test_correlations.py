import numpy as np
import pandas as pd
import pytest

from modules.ai.correlations import analizar_correlaciones, cramer_v, dependencia_cat_num
from modules.type_detector import detectar_tipos


def test_correlacion_perfecta():
    rng = np.random.default_rng(0)
    x = rng.normal(50, 10, 100)       # (una secuencia 1,2,3... se detectaria como id)
    df = pd.DataFrame({"x": x, "y": 2 * x + 1, "z": rng.normal(size=100)})
    res = analizar_correlaciones(df, detectar_tipos(df))
    top = res["tablas"]["pares_numericos"].iloc[0]
    assert {top["variable_a"], top["variable_b"]} == {"x", "y"}
    assert top["pearson"] == pytest.approx(1.0)
    assert top["fuerza"] == "fuerte"


def test_eta_cuadrado_alto_cuando_la_categoria_explica_el_numero(df_mixto):
    tabla = dependencia_cat_num(df_mixto, ["region", "ciudad"], ["edad"])
    fila_region = tabla[tabla["categorica"] == "region"].iloc[0]
    fila_ciudad = tabla[tabla["categorica"] == "ciudad"].iloc[0]
    assert fila_region["eta2"] > 0.8
    assert fila_ciudad["eta2"] < 0.1


def test_cramer_v_en_dependencia_total_y_en_independencia():
    total = pd.DataFrame([[50, 0], [0, 50]])
    v, _, _ = cramer_v(total)
    assert v > 0.95
    indep = pd.DataFrame([[25, 25], [25, 25]])
    v, _, _ = cramer_v(indep)
    assert v == pytest.approx(0.0, abs=1e-6)


def test_ranking_solo_trae_relaciones_significativas(df_mixto):
    res = analizar_correlaciones(df_mixto, detectar_tipos(df_mixto))
    ranking = res["tablas"]["ranking"]
    assert (ranking["p_valor"] < 0.05).all()
    assert (ranking["fuerza"] != "debil").all()