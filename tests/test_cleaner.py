import numpy as np
import pandas as pd

from modules.cleaner import limpiar


def _base(n=30):
    return pd.DataFrame({"x": np.arange(n, dtype=float), "y": np.arange(n) % 5})


def test_elimina_duplicados():
    df = pd.concat([_base(), _base().iloc[:3]], ignore_index=True)
    limpio, log = limpiar(df)
    assert log["duplicados_eliminados"] == 3
    assert len(limpio) == 30


def test_rellena_nulos_con_mediana():
    df = _base()
    df.loc[2, "x"] = np.nan
    limpio, _ = limpiar(df)
    assert limpio["x"].isna().sum() == 0


def test_texto_con_numeros_se_convierte():
    df = _base()
    df["precio"] = [str(v) for v in range(30)]
    limpio, log = limpiar(df)
    assert pd.api.types.is_numeric_dtype(limpio["precio"])
    assert "precio" in log["columnas_convertidas_a_numero"]


def test_fechas_con_anotacion_entre_parentesis():
    df = _base()
    df["fecha"] = ["Sat Aug 14 2010"] * 15 + ["Sun Aug 15 2010 (P)"] * 15
    limpio, _ = limpiar(df)
    assert pd.api.types.is_datetime64_any_dtype(limpio["fecha"])
    assert limpio["fecha"].isna().sum() == 0


def test_unifica_variantes_de_un_mismo_nombre():
    df = _base(60)
    df["equipo"] = (["Man United", "Man Utd", "Chelsea", "Chelsea FC"] * 15)
    limpio, log = limpiar(df)
    assert limpio["equipo"].nunique() == 2
    assert log["categorias_unificadas"]


def test_infinito_se_trata_como_dato_faltante():
    df = _base()
    df.loc[3, "x"] = np.inf
    limpio, _ = limpiar(df)
    assert np.isfinite(limpio["x"]).all()