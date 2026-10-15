# Deteccion de tipos de variables
import re
import pandas as pd
from modules import config

TIPOS_ANALIZABLES = ("numerica", "categorica", "booleana", "temporal")

def _nombre_parece_id(nombre):
    return re.search(r"(^|[^a-z])(id|codigo|código|cod|uuid)([^a-z]|$)",
                     str(nombre).lower()) is not None

def _es_entera(serie):
    
    if pd.api.types.is_integer_dtype(serie):
        return True
    return bool((serie.dropna() % 1 == 0).all())

def _tipo_numerico(serie, nombre, ratio):
    valores = set(serie.dropna().unique())
    if valores <= {0, 1}:
        return "booleana"
    if _es_entera(serie):
        if _nombre_parece_id(nombre) and ratio >= 0.9:
            return "id"
        if ratio == 1 and serie.is_monotonic_increasing:
            return "id"
    return "numerica"

def _tipo_texto(serie, nombre, ratio, unicos):
    valores = set(serie.dropna().astype(str).str.lower().str.strip().unique())
    if valores <= config.VALORES_BOOLEANOS:
        return "booleana"
    if ratio >= config.RATIO_ID:
        return "id" if _nombre_parece_id(nombre) else "texto"

    pocas_categorias = unicos <= config.MAX_CATEGORIAS and ratio <= config.RATIO_CATEGORIA
    dataset_grande = (unicos <= config.MAX_CATEGORIAS_GRANDE
                      and ratio < config.RATIO_CATEGORIA_GRANDE)
    if pocas_categorias or dataset_grande:
        return "categorica"
    return "texto"

def detectar_tipo(serie, nombre):
    datos = serie.dropna()
    unicos = int(datos.nunique())

    if unicos <= 1:
        return "constante"
    if pd.api.types.is_datetime64_any_dtype(serie):
        return "temporal"
    if pd.api.types.is_bool_dtype(serie):
        return "booleana"

    ratio = unicos / len(datos)
    if pd.api.types.is_numeric_dtype(serie):
        return _tipo_numerico(datos, nombre, ratio)
    return _tipo_texto(serie, nombre, ratio, unicos)


def detectar_tipos(df):
    return {col: detectar_tipo(df[col], col) for col in df.columns}


def columnas_por_tipo(esquema, *tipos):
    return [col for col, tipo in esquema.items() if tipo in tipos]


def resumen_tipos(esquema):
    conteo = {}
    for tipo in esquema.values():
        conteo[tipo] = conteo.get(tipo, 0) + 1
    return conteo