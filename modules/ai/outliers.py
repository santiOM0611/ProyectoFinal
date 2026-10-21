# Outliers 

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from modules import config
from modules.ai.base import resultado_base
from modules.type_detector import columnas_por_tipo

# Definicion de valores a utilizar 
def calcular_zscores(serie):
    desviacion = serie.std(ddof=0)
    if desviacion == 0:
        return pd.Series(0.0, index=serie.index)
    return (serie - serie.mean()) / desviacion

def outliers_zscore(serie, umbral=config.ZSCORE_UMBRAL):
    return calcular_zscores(serie).abs() > umbral

def rango_intercuartil(serie):
    q1, q3 = serie.quantile([0.25, 0.75])
    return q3 - q1

def outliers_iqr(serie, factor=config.IQR_FACTOR):
    q1, q3 = serie.quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        return pd.Series(False, index=serie.index)
    return (serie < q1 - factor * iqr) | (serie > q3 + factor * iqr)

def outliers_isolation_forest(datos, contaminacion=config.CONTAMINACION):
    modelo = IsolationForest(contamination=contaminacion, random_state=config.SEMILLA)
    etiquetas = modelo.fit_predict(datos)      
    puntajes = modelo.decision_function(datos)
    return etiquetas == -1, puntajes

# Deteccion automatica de los outliers
def detectar_outliers(df, esquema, contaminacion=config.CONTAMINACION):

    columnas = columnas_por_tipo(esquema, "numerica")
    if not columnas:
        return resultado_base(True, "No hay columnas numericas para buscar outliers.")

    resultado = resultado_base()
    datos = df[columnas]
    total = len(df)

    # Metodos a realizar por columna (Z-score e IQR) 
    marcas_z = {}
    marcas_iqr = {}
    z_absolutos = {}
    columnas_sin_iqr = []
    filas_tabla = []
    for col in columnas:
        z = calcular_zscores(datos[col])
        marcas_z[col] = z.abs() > config.ZSCORE_UMBRAL
        marcas_iqr[col] = outliers_iqr(datos[col])
        z_absolutos[col] = z.abs()
        if rango_intercuartil(datos[col]) == 0:
            columnas_sin_iqr.append(col)
        filas_tabla.append({
            "columna": col,
            "zscore_n": int(marcas_z[col].sum()),
            "zscore_pct": round(float(marcas_z[col].mean()) * 100, 2),
            "iqr_n": int(marcas_iqr[col].sum()),
            "iqr_pct": round(float(marcas_iqr[col].mean()) * 100, 2),
        })
    marcas_z = pd.DataFrame(marcas_z)
    marcas_iqr = pd.DataFrame(marcas_iqr)
    z_absolutos = pd.DataFrame(z_absolutos)

    por_columna = (pd.DataFrame(filas_tabla)
                   .sort_values(["iqr_n", "zscore_n"], ascending=False)
                   .reset_index(drop=True))

    # Metodos a realizar por registro Isolation Forest
    es_anomalia, puntajes = outliers_isolation_forest(datos, contaminacion)

    voto_z = marcas_z.any(axis=1)
    voto_iqr = marcas_iqr.any(axis=1)
    voto_if = pd.Series(es_anomalia, index=df.index)
    marcas = pd.DataFrame({
        "outlier_zscore": voto_z,
        "outlier_iqr": voto_iqr,
        "outlier_isolation_forest": voto_if,
        "puntaje_isolation_forest": puntajes,
    })
    marcas["votos"] = (voto_z.astype(int) + voto_iqr.astype(int) + voto_if.astype(int))
    marcas["es_outlier"] = voto_if & (voto_z | voto_iqr)

    candidatos = marcas[marcas["es_outlier"]].sort_values("puntaje_isolation_forest")
    candidatos = candidatos.head(config.MAX_OUTLIERS_TABLA)
    variables_extremas = z_absolutos.loc[candidatos.index].idxmax(axis=1)
    registros = pd.DataFrame({
        "fila": candidatos.index,
        "votos": candidatos["votos"].to_numpy(),
        "puntaje_if": candidatos["puntaje_isolation_forest"].round(3).to_numpy(),
        "variable_mas_extrema": variables_extremas.to_numpy(),
        "z_maximo": [round(float(z_absolutos.loc[i, v]), 2)
                     for i, v in variables_extremas.items()],
        "valor": [df.loc[i, v] for i, v in variables_extremas.items()],
    })

    # Resultado
    n_outliers = int(marcas["es_outlier"].sum())
    afectadas = por_columna[por_columna["iqr_n"] > 0]["columna"].head(3).tolist()
    resultado["resumen"] = {
        "filas": total,
        "columnas_analizadas": len(columnas),
        "n_outliers": n_outliers,
        "pct_outliers": round(n_outliers / total * 100, 2),
        "n_isolation_forest": int(voto_if.sum()),
        "n_filas_con_zscore": int(voto_z.sum()),
        "n_filas_con_iqr": int(voto_iqr.sum()),
        "columnas_mas_afectadas": afectadas,
    }
    resultado["tablas"] = {"por_columna": por_columna, "registros": registros}
    resultado["datos_graficos"] = {"marcas": marcas}

    if columnas_sin_iqr:
        muestra = ", ".join(columnas_sin_iqr[:5])
        resultado["advertencias"].append(
            f"IQR no se pudo aplicar en {len(columnas_sin_iqr)} columna(s) porque mas de "
            f"la mitad de sus valores son iguales (ej: {muestra})."
        )
    return resultado