from modules.ai.clustering import agrupar
from modules.ai.correlations import analizar_correlaciones
from modules.ai.outliers import detectar_outliers
from modules.cleaner import limpiar
from modules.insights import generar_hallazgos
from modules.loader import cargar_archivo
from modules.stats import calcular_estadisticas
from modules.type_detector import detectar_tipos, resumen_tipos
from modules.viz import generar_figuras


def analizar_dataframe(df, metadata, excluir_clustering=()):
    df_limpio, log = limpiar(df)
    esquema = detectar_tipos(df_limpio)
    estadisticas = calcular_estadisticas(df_limpio, esquema)

    outliers = detectar_outliers(df_limpio, esquema)
    mascara = None if outliers["omitido"] else outliers["datos_graficos"]["marcas"]["es_outlier"]
    clustering = agrupar(df_limpio, esquema, mascara, excluir=tuple(excluir_clustering))
    correlaciones = analizar_correlaciones(df_limpio, esquema)
    resultados_ia = {"outliers": outliers, "clustering": clustering,
                     "correlaciones": correlaciones}

    figuras = generar_figuras(df_limpio, esquema, log, resultados_ia)
    hallazgos = generar_hallazgos(log, esquema, estadisticas, resultados_ia)

    return {
        "metadata": metadata,
        "log": log,
        "df": df_limpio,
        "esquema": esquema,
        "conteo_tipos": resumen_tipos(esquema),
        "estadisticas": estadisticas,
        "outliers": outliers,
        "clustering": clustering,
        "correlaciones": correlaciones,
        "figuras": figuras,
        "hallazgos": hallazgos,
        "columnas_ignoradas": [c for c in excluir_clustering if c in df_limpio.columns],
    }

def analizar_archivo(ruta, hoja=None, excluir_clustering=()):
    df, metadata = cargar_archivo(ruta, hoja)
    return analizar_dataframe(df, metadata, excluir_clustering)

def datos_enriquecidos(resultado):
    df = resultado["df"].copy()
    if not resultado["outliers"]["omitido"]:
        df["es_outlier"] = resultado["outliers"]["datos_graficos"]["marcas"]["es_outlier"]
    if not resultado["clustering"]["omitido"]:
        etiquetas = resultado["clustering"]["tablas"]["etiquetas"]
        df["cluster_kmeans"] = etiquetas["cluster_kmeans"]
        df["cluster_dbscan"] = etiquetas["cluster_dbscan"]
    return df