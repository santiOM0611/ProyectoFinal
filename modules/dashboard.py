
#Modulo 10: constructor del dashboard HTML.


import datetime
import os

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from plotly.offline import get_plotlyjs, get_plotlyjs_version

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_PLANTILLAS = os.path.join(RAIZ, "templates")

_entorno = Environment(
    loader=FileSystemLoader(CARPETA_PLANTILLAS),
    autoescape=select_autoescape(["html"]),
)

ETIQUETAS_CATEGORIA = {
    "calidad": "Calidad de datos", "descriptivo": "Descriptivo", "outliers": "Outliers",
    "clustering": "Clustering", "correlaciones": "Relaciones",
}
ETIQUETAS_NIVEL = {"alto": "Importante", "medio": "Relevante", "bajo": "Informativo"}

ETIQUETAS_COLUMNAS = {
    "desviacion": "desviación", "minimo": "mínimo", "maximo": "máximo", "asimetria": "asimetría",
    "puntaje_if": "puntaje IF", "variable_mas_extrema": "variable más extrema",
    "z_maximo": "z máximo", "zscore_n": "Z-score (n)", "zscore_pct": "Z-score (%)",
    "iqr_n": "IQR (n)", "iqr_pct": "IQR (%)", "direccion": "dirección",
    "diferencia_desv": "diferencia (desv.)", "p_valor": "p-valor", "categorica": "categórica",
    "numerica": "numérica",
}

NOMBRES_TIPO = {
    "numerica": ("numérica", "numéricas"), "categorica": ("categórica", "categóricas"),
    "booleana": ("booleana", "booleanas"), "temporal": ("de fecha", "de fecha"),
    "id": ("identificador", "identificadores"), "texto": ("de texto", "de texto"),
    "constante": ("constante", "constantes"),
}



# Formato de valores y tablas
def formatear_valor(valor):
    """Convierte cualquier valor de una tabla en un texto legible."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    if isinstance(valor, (bool, np.bool_)):
        return "Sí" if valor else "No"
    if isinstance(valor, (pd.Timestamp, datetime.datetime)):
        return f"{valor:%d/%m/%Y}"
    if isinstance(valor, (int, np.integer)):
        return str(int(valor))
    if isinstance(valor, (float, np.floating)):
        valor = float(valor)
        if valor == int(valor) and abs(valor) < 1e15:
            return str(int(valor))
        if abs(valor) < 0.001:
            return f"{valor:.1e}"
        if abs(valor) < 1:
            return f"{valor:.3f}"
        if abs(valor) < 1000:
            return f"{valor:.2f}"
        return f"{valor:.1f}"
    return str(valor)


def _decimales_columna(serie):
    absolutos = serie.dropna().abs()
    if absolutos.empty:
        return 2
    if absolutos.max() < 1:
        return 3
    return 1 if absolutos.min() >= 1000 else 2


def tabla_a_dict(df, max_filas=None, con_indice=False, nombre_indice="variable"):
   
    if df is None or df.empty:
        return None
    total = len(df)
    if max_filas:
        df = df.head(max_filas)
    if con_indice:
        df = df.rename_axis(nombre_indice).reset_index()

    columnas = list(df.columns)
    decimales = {c: _decimales_columna(df[c]) for c in columnas
                 if pd.api.types.is_float_dtype(df[c])}
    filas = []
    for fila in df.itertuples(index=False):
        celdas = []
        for nombre, valor in zip(columnas, fila):
            if nombre == "p_valor" and isinstance(valor, (float, np.floating)):
                celdas.append("<0.001" if valor < 0.001 else f"{valor:.3f}")
            elif nombre in decimales and pd.notna(valor):
                celdas.append(f"{valor:.{decimales[nombre]}f}")
            else:
                celdas.append(formatear_valor(valor))
        filas.append(celdas)
    return {
        "columnas": [ETIQUETAS_COLUMNAS.get(c, str(c).replace("_", " ")) for c in columnas],
        "filas": filas,
        "numericas": [pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
                      for c in columnas],
        "total": total,
    }


# Piezas de la pagina
def _kpis(resultado):
    log, tipos = resultado["log"], resultado["conteo_tipos"]
    outliers, clustering = resultado["outliers"], resultado["clustering"]
    kpis = [
        {"etiqueta": "Filas", "valor": log["filas_finales"],
         "nota": f"de {log['filas_originales']} originales"},
        {"etiqueta": "Columnas", "valor": log["columnas_finales"],
         "nota": f"de {log['columnas_originales']} originales"},
        {"etiqueta": "Numéricas", "valor": tipos.get("numerica", 0), "nota": "variables"},
        {"etiqueta": "Categóricas", "valor": tipos.get("categorica", 0) + tipos.get("booleana", 0),
         "nota": "variables"},
    ]
    if outliers["omitido"]:
        kpis.append({"etiqueta": "Outliers", "valor": "—", "nota": "no aplica"})
    else:
        r = outliers["resumen"]
        kpis.append({"etiqueta": "Outliers", "valor": r["n_outliers"],
                     "nota": f"{r['pct_outliers']}% de las filas"})
    if clustering["omitido"]:
        kpis.append({"etiqueta": "Grupos", "valor": "—", "nota": "no aplica"})
    else:
        r = clustering["resumen"]
        kpis.append({"etiqueta": "Grupos (K-means)", "valor": r["kmeans_k"],
                     "nota": f"silhouette {r['kmeans_silhouette']}"})
    return kpis


def _pasos_limpieza(log):
    def nombres(valor):
        elementos = list(valor.keys()) if isinstance(valor, dict) else list(valor)
        return ", ".join(str(e) for e in elementos[:6]) + (" …" if len(elementos) > 6 else "")

    imputados = sum(v["cantidad"] for v in log.get("imputaciones", {}).values())
    pasos = [
        ("Filas duplicadas eliminadas", log["duplicados_eliminados"], ""),
        ("Filas completamente vacías eliminadas", log["filas_vacias_eliminadas"], ""),
        ("Columnas vacías eliminadas", len(log["columnas_vacias_eliminadas"]),
         nombres(log["columnas_vacias_eliminadas"])),
        ("Columnas con demasiados nulos eliminadas", len(log["columnas_eliminadas_por_nulos"]),
         nombres(log["columnas_eliminadas_por_nulos"])),
        ("Columnas de texto convertidas a número", len(log["columnas_convertidas_a_numero"]),
         nombres(log["columnas_convertidas_a_numero"])),
        ("Columnas de texto convertidas a fecha", len(log["columnas_convertidas_a_fecha"]),
         nombres(log["columnas_convertidas_a_fecha"])),
        ("Nombres de columnas corregidos", len(log["columnas_renombradas"]),
         nombres(log["columnas_renombradas"])),
        ("Valores faltantes rellenados", imputados,
         f"en {len(log.get('imputaciones', {}))} columna(s)" if imputados else ""),
    ]
    return pd.DataFrame(pasos, columns=["Acción", "Cantidad", "Detalle"])


def _categoricas(estadisticas, maximo=12):
    tarjetas = []
    for columna, info in list(estadisticas["categoricas"].items())[:maximo]:
        tarjetas.append({
            "columna": columna, "unicos": info["unicos"], "moda": formatear_valor(info["moda"]),
            "tabla": tabla_a_dict(info["top"]),
        })
    return tarjetas


def _html_figuras(figuras):
    return {nombre: Markup(fig.to_html(full_html=False, include_plotlyjs=False,
                                       config={"displaylogo": False, "responsive": True}))
            for nombre, fig in figuras.items()}



# Funcion principal del modulo
def construir_dashboard(resultado, embebido=False, enlaces=None):

    estadisticas, outliers = resultado["estadisticas"], resultado["outliers"]
    clustering, correlaciones = resultado["clustering"], resultado["correlaciones"]

    if embebido:
        script_plotly = Markup("<script>" + get_plotlyjs() + "</script>")
    else:
        script_plotly = Markup(
            f'<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js"></script>')

    hallazgos = [dict(h, categoria_texto=ETIQUETAS_CATEGORIA[h["categoria"]],
                      nivel_texto=ETIQUETAS_NIVEL[h["nivel"]]) for h in resultado["hallazgos"]]

    tipos = pd.DataFrame({"variable": list(resultado["esquema"].keys()),
                          "tipo": list(resultado["esquema"].values())})

    contexto = {
        "metadata": resultado["metadata"],
        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "script_plotly": script_plotly,
        "enlaces": enlaces or {},
        "kpis": _kpis(resultado),
        "hallazgos": hallazgos,
        "tabla_limpieza": tabla_a_dict(_pasos_limpieza(resultado["log"])),
        "conteo_tipos": [(n, NOMBRES_TIPO.get(t, (t, t))[0 if n == 1 else 1])
                         for t, n in resultado["conteo_tipos"].items()],
        "tabla_tipos": tabla_a_dict(tipos),
        "tabla_numericas": tabla_a_dict(estadisticas["numericas"], max_filas=40, con_indice=True),
        "categoricas": _categoricas(estadisticas),
        "total_categoricas": len(estadisticas["categoricas"]),
        "temporales": [{"columna": c, "minimo": formatear_valor(i["minimo"]),
                        "maximo": formatear_valor(i["maximo"]), "dias": i["rango_dias"]}
                       for c, i in estadisticas["temporales"].items()],
        "outliers": outliers,
        "tabla_outliers_columna": (None if outliers["omitido"] else
                                   tabla_a_dict(outliers["tablas"]["por_columna"], max_filas=15)),
        "tabla_outliers_registros": (None if outliers["omitido"] else
                                     tabla_a_dict(outliers["tablas"]["registros"])),
        "clustering": clustering,
        "tabla_tamanos": (None if clustering["omitido"] else
                          tabla_a_dict(clustering["tablas"]["tamanos"])),
        "tabla_distintivas": (None if clustering["omitido"] else
                              tabla_a_dict(clustering["tablas"]["distintivas"])),
        "columnas_ignoradas": resultado["columnas_ignoradas"],
        "correlaciones": correlaciones,
        "tabla_ranking": (None if correlaciones["omitido"] else
                          tabla_a_dict(correlaciones["tablas"]["ranking"])),
        "graficos": _html_figuras(resultado["figuras"]),
    }
    return _entorno.get_template("reporte.html").render(**contexto)


def guardar_dashboard(resultado, ruta_salida, embebido=True):
    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write(construir_dashboard(resultado, embebido=embebido))
    return ruta_salida