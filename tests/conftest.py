"""Datos de ejemplo compartidos por las pruebas (se crean al vuelo, sin archivos)."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def df_mixto():
    """200 filas con 2 grupos claros, una columna categorica y un outlier plantado."""
    rng = np.random.default_rng(0)
    n = 200
    grupo = np.repeat([0, 1], n // 2)
    df = pd.DataFrame({
        "edad": rng.normal(30 + 25 * grupo, 3),
        "gasto": rng.normal(100 + 400 * grupo, 20),
        "ruido": rng.normal(0, 1, n),
        "region": np.where(grupo == 0, "Norte", "Sur"),
        "ciudad": rng.choice(["A", "B", "C"], n),
    })
    df.loc[0, "ruido"] = 40.0      # outlier extremo
    df.loc[0, "gasto"] = 5000.0
    return df


@pytest.fixture
def csv_mixto(tmp_path, df_mixto):
    ruta = tmp_path / "datos.csv"
    df_mixto.to_csv(ruta, index=False)
    return str(ruta)
