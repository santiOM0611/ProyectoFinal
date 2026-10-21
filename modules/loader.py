# Carga de datos
import csv
import os

import pandas as pd

from modules import config


class ErrorDeCarga(Exception):
    pass

def _validar_ruta(ruta):
    if not os.path.isfile(ruta):
        raise ErrorDeCarga(f"No se encontro el archivo: {ruta}")

    extension = os.path.splitext(ruta)[1].lower()
    if extension not in config.EXTENSIONES_PERMITIDAS:
        permitidas = ", ".join(config.EXTENSIONES_PERMITIDAS)
        raise ErrorDeCarga(f"Formato no soportado ({extension}). Usa: {permitidas}")
    return extension


def _detectar_separador(ruta, codificacion):
    with open(ruta, "r", encoding=codificacion, errors="replace", newline="") as archivo:
        muestra = archivo.read(5000)
    if "\n" in muestra:
        muestra = muestra.rsplit("\n", 1)[0] 
    try:
        return csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","  


def _leer_csv(ruta):
    for codificacion in config.CODIFICACIONES:
        try:
            separador = _detectar_separador(ruta, codificacion)
            return pd.read_csv(ruta, sep=separador, encoding=codificacion)
        except UnicodeDecodeError:
            continue  
        except pd.errors.EmptyDataError as error:
            raise ErrorDeCarga("El archivo esta vacio.") from error
        except pd.errors.ParserError as error:
            raise ErrorDeCarga(f"El CSV tiene un formato invalido: {error}") from error
    raise ErrorDeCarga("No se pudo determinar la codificacion del archivo.")


def _leer_excel(ruta, hoja):
    try:
        return pd.read_excel(ruta, sheet_name=hoja if hoja is not None else 0)
    except ValueError as error:
        raise ErrorDeCarga(f"No se pudo leer la hoja '{hoja}': {error}") from error
    except Exception as error:
        raise ErrorDeCarga(f"No se pudo leer el Excel: {error}") from error


def listar_hojas(ruta):
    extension = _validar_ruta(ruta)
    if extension == ".csv":
        return []
    try:
        with pd.ExcelFile(ruta) as libro:
            return libro.sheet_names
    except Exception as error:
        raise ErrorDeCarga(f"No se pudo leer el Excel: {error}") from error


def cargar_archivo(ruta, hoja=None):
    extension = _validar_ruta(ruta)

    if extension == ".csv":
        df = _leer_csv(ruta)
        hojas = []
    else:
        df = _leer_excel(ruta, hoja)
        hojas = listar_hojas(ruta)

    if df.empty:
        raise ErrorDeCarga("El archivo no tiene datos.")
    if df.shape[1] < config.MIN_COLUMNAS:
        raise ErrorDeCarga(
            f"El archivo tiene {df.shape[1]} columna(s); se necesitan al menos "
            f"{config.MIN_COLUMNAS}. Revisa el separador del CSV."
        )
    if df.shape[0] < config.MIN_FILAS:
        raise ErrorDeCarga(
            f"El archivo tiene {df.shape[0]} fila(s); se necesitan al menos "
            f"{config.MIN_FILAS}."
        )

    metadata = {
        "nombre": os.path.basename(ruta),
        "extension": extension,
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "tamano_mb": round(os.path.getsize(ruta) / (1024 * 1024), 3),
        "hoja": hoja if hoja is not None else (hojas[0] if hojas else None),
        "hojas_disponibles": hojas,
    }
    return df, metadata


def cargar_varios(rutas):
    resultados = {}
    errores = {}
    for ruta in rutas:
        nombre = os.path.basename(ruta)
        try:
            resultados[nombre] = cargar_archivo(ruta)
        except ErrorDeCarga as error:
            errores[nombre] = str(error)
    return resultados, errores