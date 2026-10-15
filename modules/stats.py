import pandas as pd
from modules import config
from modules.type_detector import columnas_por_tipo


def estadisticas_numericas(df, columnas):
    if not columnas:
        return pd.DataFrame()
    datos = df[columnas]
    resumen = pd.DataFrame({
        "conteo": datos.count(),
        "media": datos.mean(),
        "mediana": datos.median(),
        "desviacion": datos.std(),
        "minimo": datos.min(),
        "q1": datos.quantile(0.25),
        "q3": datos.quantile(0.75),
        "maximo": datos.max(),
        "asimetria": datos.skew(),
        "curtosis": datos.kurt(),
    })
    return resumen.round(2)


def estadisticas_categoricas(df, columnas):
    resultado = {}
    for col in columnas:
        frecuencias = df[col].value_counts(dropna=True)
        if frecuencias.empty:
            continue
        total = frecuencias.sum()
        top = (frecuencias.head(config.TOP_CATEGORIAS)
               .rename_axis("valor")
               .reset_index(name="frecuencia"))
        top["porcentaje"] = (top["frecuencia"] / total * 100).round(1)
        resultado[col] = {
            "unicos": int(df[col].nunique()),
            "moda": frecuencias.index[0],
            "top": top,
        }
    return resultado


def estadisticas_temporales(df, columnas):
    resultado = {}
    for col in columnas:
        minimo, maximo = df[col].min(), df[col].max()
        resultado[col] = {
            "minimo": minimo,
            "maximo": maximo,
            "rango_dias": int((maximo - minimo).days),
        }
    return resultado


def calcular_estadisticas(df, esquema):
    return {
        "numericas": estadisticas_numericas(
            df, columnas_por_tipo(esquema, "numerica")),
        "categoricas": estadisticas_categoricas(
            df, columnas_por_tipo(esquema, "categorica", "booleana")),
        "temporales": estadisticas_temporales(
            df, columnas_por_tipo(esquema, "temporal")),
        "excluidas": {col: tipo for col, tipo in esquema.items()
                      if tipo in ("id", "texto", "constante")},
    }