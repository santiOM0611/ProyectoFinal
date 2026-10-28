# Clustering

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from modules import config
from modules.ai.base import resultado_base
from modules.type_detector import columnas_por_tipo


def interpretar_silhouette(valor):
    if valor >= 0.5:
        return "grupos bien definidos"
    if valor >= 0.25:
        return "grupos con separacion debil"
    return "sin una estructura de grupos clara"

# K-means
def ejecutar_kmeans(X):

    n = len(X)
    k_maximo = min(config.K_MAX, n - 1)
    muestra = config.MUESTRA_SILHOUETTE if n > config.MUESTRA_SILHOUETTE else None

    filas = []
    etiquetas_por_k = {}
    for k in range(config.K_MIN, k_maximo + 1):
        modelo = KMeans(n_clusters=k, n_init=10, random_state=config.SEMILLA).fit(X)
        puntaje = silhouette_score(X, modelo.labels_, sample_size=muestra,
                                   random_state=config.SEMILLA)
        filas.append({"k": k, "silhouette": float(puntaje), "inercia": float(modelo.inertia_)})
        etiquetas_por_k[k] = modelo.labels_

    tabla = pd.DataFrame(filas)
    mejor_k = int(tabla.loc[tabla["silhouette"].idxmax(), "k"])
    return tabla, etiquetas_por_k[mejor_k]

# DBSCAN
def estimar_eps(X, min_muestras):
    vecinos = NearestNeighbors(n_neighbors=min_muestras).fit(X)
    distancias, _ = vecinos.kneighbors(X)
    ultima = distancias[:, -1]
    eps = float(np.percentile(ultima, 90))
    if eps <= 0:
        positivas = ultima[ultima > 0]
        eps = float(np.median(positivas)) if len(positivas) else 0.5
    return eps


def ejecutar_dbscan(X):
    min_muestras = int(min(50, max(config.DBSCAN_MIN_MUESTRAS, round(0.02 * len(X)))))
    eps = estimar_eps(X, min_muestras)
    modelo = DBSCAN(eps=eps, min_samples=min_muestras).fit(X)
    return modelo.labels_, eps, min_muestras


# Perfil de cada grupo
def perfilar_clusters(datos, etiquetas):
    media_global = datos.mean()
    desviacion_global = datos.std(ddof=0)
    medias = datos.groupby(etiquetas).mean()
    diferencias = (medias - media_global) / desviacion_global

    conteo = pd.Series(etiquetas).value_counts().sort_index()
    tamanos = pd.DataFrame({
        "cluster": conteo.index,
        "filas": conteo.to_numpy(),
        "porcentaje": (conteo / conteo.sum() * 100).round(1).to_numpy(),
    })

    filas = []
    for cluster in diferencias.index:
        top = diferencias.loc[cluster].abs().sort_values(ascending=False)
        for variable in top.head(config.TOP_VARIABLES_CLUSTER).index:
            diferencia = diferencias.loc[cluster, variable]
            filas.append({
                "cluster": cluster,
                "variable": variable,
                "direccion": "alto" if diferencia > 0 else "bajo",
                "diferencia_desv": round(float(diferencia), 2),
                "media_cluster": round(float(medias.loc[cluster, variable]), 2),
                "media_global": round(float(media_global[variable]), 2),
            })
    return tamanos, pd.DataFrame(filas), diferencias


# Funcion principal del modulo
def agrupar(df, esquema, mascara_excluir=None, excluir=()):
    columnas = [c for c in columnas_por_tipo(esquema, "numerica")
                if df[c].std() > 0 and c not in excluir]
    if len(columnas) < config.MIN_COLUMNAS_CLUSTERING:
        return resultado_base(
            True, "Se necesitan al menos 2 columnas numericas para agrupar.")

    if mascara_excluir is None:
        usar = np.ones(len(df), dtype=bool)
    else:
        usar = ~np.asarray(mascara_excluir, dtype=bool)
    if usar.sum() < config.MIN_FILAS_CLUSTERING:
        return resultado_base(
            True, f"Se necesitan al menos {config.MIN_FILAS_CLUSTERING} registros para agrupar.")

    resultado = resultado_base()

    datos_usados = df.loc[usar, columnas]
    escalador = StandardScaler().fit(datos_usados)
    X = escalador.transform(datos_usados)

    puntajes, etiquetas_km = ejecutar_kmeans(X)
    etiquetas_db, eps, min_muestras = ejecutar_dbscan(X)

    pca = PCA(n_components=2, random_state=config.SEMILLA).fit(X)
    coordenadas = pca.transform(escalador.transform(df[columnas]))

    tamanos, distintivas, diferencias = perfilar_clusters(datos_usados, etiquetas_km)

    completas_km = np.full(len(df), -1)
    completas_km[usar] = etiquetas_km
    completas_db = np.full(len(df), -1)
    completas_db[usar] = etiquetas_db
    etiquetas = pd.DataFrame({"cluster_kmeans": completas_km,
                              "cluster_dbscan": completas_db}, index=df.index)

    mejor = puntajes.loc[puntajes["silhouette"].idxmax()]
    n_grupos_db = len(set(etiquetas_db)) - (1 if -1 in set(etiquetas_db) else 0)
    resultado["resumen"] = {
        "variables_usadas": len(columnas),
        "filas_usadas": int(usar.sum()),
        "filas_excluidas": int((~usar).sum()),
        "kmeans_k": int(mejor["k"]),
        "kmeans_silhouette": round(float(mejor["silhouette"]), 3),
        "kmeans_interpretacion": interpretar_silhouette(float(mejor["silhouette"])),
        "dbscan_grupos": n_grupos_db,
        "dbscan_ruido": int((etiquetas_db == -1).sum()),
        "dbscan_eps": round(eps, 3),
        "dbscan_min_muestras": min_muestras,
        "varianza_explicada_pca": round(float(pca.explained_variance_ratio_.sum()) * 100, 1),
    }
    resultado["tablas"] = {
        "etiquetas": etiquetas,
        "tamanos": tamanos,
        "distintivas": distintivas,
        "silhouette_por_k": puntajes,
    }
    resultado["datos_graficos"] = {
        "pca": pd.DataFrame(coordenadas, columns=["pc1", "pc2"], index=df.index),
        "etiquetas": etiquetas,
        "diferencias": diferencias,
        "silhouette_por_k": puntajes,
        "k_elegido": int(mejor["k"]),
        "varianza_pca": [round(float(v) * 100, 1) for v in pca.explained_variance_ratio_],
    }

    if mejor["silhouette"] < 0.25:
        resultado["advertencias"].append(
            "Los grupos de K-means no estan bien separados (silhouette bajo): "
            "los datos podrian no tener una estructura de grupos clara.")
    if n_grupos_db <= 1:
        resultado["advertencias"].append(
            "DBSCAN encontro como maximo un grupo: los datos forman una sola nube densa.")
    return resultado