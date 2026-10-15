# Modulo 2: limpieza basica.
import re
import warnings
import pandas as pd

from modules import config

# Deja el DataFrame listo para analizar y registra todo lo que cambio
# en un diccionario (log), porque eso se muestra luego en el reporte.

# Texto que parece fecha: 2024-01-31, 31/01/2024, 31.1.24
PATRON_FECHA = r"^\s*\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"

# True si la columna es de texto o de tipo object (que puede ser texto)
def _es_texto(serie):
    return pd.api.types.is_string_dtype(serie) or serie.dtype == object

# Quita espacios sobrantes, rellena nombres vacios y evita repetidos
def _limpiar_nombres(df, log):
    nuevos = []
    for numero, nombre in enumerate(df.columns, start=1):
        limpio = re.sub(r"\s+", " ", str(nombre)).strip()
        if limpio == "" or limpio.startswith("Unnamed"):
            limpio = f"columna_{numero}"
        base = limpio
        repeticion = 2
        while limpio in nuevos:
            limpio = f"{base}_{repeticion}"
            repeticion += 1
        nuevos.append(limpio)

    renombradas = {a: b for a, b in zip(df.columns, nuevos) if str(a) != b}
    log["columnas_renombradas"] = renombradas
    df.columns = nuevos
    return df

# Quita espacios en los textos y convierte textos vacios en nulos.
def _limpiar_texto(df):
    for col in df.columns:
        if _es_texto(df[col]):
            df[col] = df[col].astype("string").str.strip().replace("", pd.NA)
    return df

# Intenta convertir texto como $1,234.50, 15% o 12,5 a numero. 
# Devuelve una Serie numerica (con NaN donde no pudo convertir).
def _texto_a_numero(serie):
    texto = serie.astype(object)

    texto = texto.replace(r"[\$€£%\s]", "", regex=True) # quitar simbolos de moneda, porcentaje y espacios
    texto = texto.replace(r"(?<=\d),(?=\d{3}(?:,|\.|$))", "", regex=True) # quitar comas de miles:  1,234  ->  1234
    texto = texto.replace(r"(?<=\d),(?=\d)", ".", regex=True)  # coma decimal -> punto:  12,5  ->  12.5 
    return pd.to_numeric(texto, errors="coerce")

# Convierte columnas de texto que en realidad son numeros.
def _convertir_numeros(df, log):
    convertidas = []
    for col in df.columns:
        if not _es_texto(df[col]):
            continue
        original = df[col].dropna()
        if original.empty:
            continue
        if original.astype(str).str.match(r"^0\d").any(): # Codigos como '00123' no se deben convertir (se perderian los ceros)
            continue
        convertida = _texto_a_numero(df[col])
        proporcion = convertida.notna().sum() / len(original)
        if proporcion >= config.UMBRAL_CONVERSION:
            df[col] = convertida
            convertidas.append(col)
    log["columnas_convertidas_a_numero"] = convertidas
    return df

# Convierte columnas de texto que en realidad son fechas.
def _convertir_fechas(df, log):
    convertidas = []
    for col in df.columns:
        if not _es_texto(df[col]):
            continue
        original = df[col].dropna()
        if original.empty:
            continue
        parece_fecha = original.astype(str).str.match(PATRON_FECHA).mean() # Primero verificamos que el texto se vea como fecha
        if parece_fecha < config.UMBRAL_CONVERSION:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            convertida = pd.to_datetime(
                df[col].astype(object), errors="coerce", dayfirst=True, format="mixed"
            )
        if convertida.notna().sum() / len(original) >= config.UMBRAL_CONVERSION:
            df[col] = convertida
            convertidas.append(col)
    log["columnas_convertidas_a_fecha"] = convertidas
    return df

# Rellena los nulos: mediana en numericas, moda en categoricas.
def _imputar(df, log):
    imputaciones = {}
    for col in df.columns:
        nulos = int(df[col].isna().sum())
        if nulos == 0:
            continue

        serie = df[col]
        if pd.api.types.is_datetime64_any_dtype(serie):
            # inventar fechas no tiene sentido: se dejan como estan
            imputaciones[col] = {"metodo": "sin imputar (fecha)", "valor": None,
                                 "cantidad": nulos}
            continue

        if pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie):
            valor = float(serie.median())
            metodo = "mediana"
        else:
            moda = serie.mode()
            if len(moda) > 0:
                valor = moda.iloc[0]
                metodo = "moda"
            else:
                valor = config.VALOR_DESCONOCIDO
                metodo = "valor fijo"

        df[col] = serie.fillna(valor)
        imputaciones[col] = {"metodo": metodo, "valor": valor, "cantidad": nulos}
    log["imputaciones"] = imputaciones
    return df

# Limpia un DataFrame. Devuelve (df_limpio, log). 
def limpiar(df):

    df = df.copy()  # Nunca tocar el original
    log = {
        "filas_originales": int(df.shape[0]),
        "columnas_originales": int(df.shape[1]),
    }

    df = _limpiar_nombres(df, log)
    df = _limpiar_texto(df)

    # filas y columnas completamente vacias
    columnas_antes = set(df.columns)
    df = df.dropna(axis=1, how="all")
    log["columnas_vacias_eliminadas"] = sorted(columnas_antes - set(df.columns))
    filas_antes = len(df)
    df = df.dropna(axis=0, how="all")
    log["filas_vacias_eliminadas"] = filas_antes - len(df)

    df = _convertir_numeros(df, log)
    df = _convertir_fechas(df, log)

    # duplicados
    filas_antes = len(df)
    df = df.drop_duplicates()
    log["duplicados_eliminados"] = filas_antes - len(df)
    df = df.reset_index(drop=True)

    # columnas con demasiados nulos
    porcentaje_nulos = df.isna().mean()
    log["nulos_por_columna"] = {
        col: {"cantidad": int(df[col].isna().sum()),
              "porcentaje": round(float(porcentaje_nulos[col]) * 100, 2)}
        for col in df.columns if df[col].isna().any()
    }
    excesivas = [c for c in df.columns if porcentaje_nulos[c] > config.MAX_NULOS_COLUMNA]
    log["columnas_eliminadas_por_nulos"] = excesivas
    df = df.drop(columns=excesivas)

    df = _imputar(df, log)

    log["filas_finales"] = int(df.shape[0])
    log["columnas_finales"] = int(df.shape[1])
    return df, log