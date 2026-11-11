import numpy as np
import pandas as pd

from modules.type_detector import columnas_por_tipo, detectar_tipos


def test_detecta_cada_tipo():
    n = 100
    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "id_cliente": np.arange(1, n + 1),
        "edad": rng.normal(40, 10, n),
        "region": rng.choice(["N", "S", "E"], n),
        "activo": rng.choice([0, 1], n),
        "fecha": pd.date_range("2024-01-01", periods=n),
        "fijo": ["igual"] * n,
    })
    esquema = detectar_tipos(df)
    assert esquema["id_cliente"] == "id"
    assert esquema["edad"] == "numerica"
    assert esquema["region"] == "categorica"
    assert esquema["activo"] == "booleana"
    assert esquema["fecha"] == "temporal"
    assert esquema["fijo"] == "constante"
    assert columnas_por_tipo(esquema, "numerica") == ["edad"]
    