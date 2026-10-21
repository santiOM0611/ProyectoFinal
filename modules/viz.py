#Graficos

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modules import config
from modules.type_detector import columnas_por_tipo


COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
           "#e87ba4", "#008300", "#6250d6", "#e34948"]
SIMBOLOS = ["circle", "diamond", "square", "triangle-up",
            "cross", "x", "star", "hexagon"]
AZUL = COLORES[0]
NARANJA = COLORES[1]

SUPERFICIE = "#fcfcfb"   
TINTA = "#0b0b0b"        
TINTA_SEC = "#52514e"   
APAGADO = "#898781"      
CUADRICULA = "#e1e0d9"
LINEA_EJE = "#c3c2b7"


DIVERGENTE = [[0.0, "#1c5cab"], [0.25, "#86b6ef"], [0.5, "#f0efec"],
              [0.75, "#ee9a99"], [1.0, "#e34948"]]


def _estilo(fig, titulo, alto=None, leyenda=False):
    fig.update_layout(
        title=dict(text=titulo, x=0.01, xanchor="left",
                   font=dict(size=16, color=TINTA)),
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif",
                  size=12, color=TINTA_SEC),
        margin=dict(l=60, r=30, t=70, b=50),
        showlegend=leyenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0.01),
        hoverlabel=dict(bgcolor=SUPERFICIE, font=dict(color=TINTA)),
    )
    if alto:
        fig.update_layout(height=alto)
    fig.update_xaxes(gridcolor=CUADRICULA, linecolor=LINEA_EJE, zeroline=False,
                     tickfont=dict(color=APAGADO))
    fig.update_yaxes(gridcolor=CUADRICULA, linecolor=LINEA_EJE, zeroline=False,
                     tickfont=dict(color=APAGADO))
    return fig


def _cuadricula(total, columnas=3):
    columnas = min(columnas, total)
    filas = math.ceil(total / columnas)
    return filas, columnas


def _subtitulos_pequenos(fig):
    fig.update_annotations(font=dict(size=12, color=TINTA_SEC))



def grafico_nulos(log_limpieza):
    nulos = log_limpieza.get("nulos_por_columna", {})
    if not nulos:
        return None
    tabla = pd.DataFrame({
        "columna": list(nulos.keys()),
        "porcentaje": [v["porcentaje"] for v in nulos.values()],
    }).sort_values("porcentaje", ascending=False).head(15)

    fig = go.Figure(go.Bar(
        x=tabla["porcentaje"].tolist(), y=tabla["columna"].tolist(), orientation="h",
        marker=dict(color=AZUL, line=dict(color=SUPERFICIE, width=1)),
        hovertemplate="%{y}: %{x:.1f}% de nulos<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="% de valores nulos")
    return _estilo(fig, "Valores nulos por columna (antes de limpiar)",
                   alto=max(300, 28 * len(tabla) + 120))


def grafico_histogramas(df, esquema):
    columnas = columnas_por_tipo(esquema, "numerica")[:config.MAX_HISTOGRAMAS]
    if not columnas:
        return None
    filas, cols = _cuadricula(len(columnas), 3)
    fig = make_subplots(rows=filas, cols=cols, subplot_titles=columnas,
                        vertical_spacing=0.12, horizontal_spacing=0.08)
    for numero, col in enumerate(columnas):
        fig.add_trace(go.Histogram(
            x=df[col].tolist(),
            marker=dict(color=AZUL, line=dict(color=SUPERFICIE, width=1)),
            hovertemplate="%{x}: %{y} registros<extra></extra>",
        ), row=numero // cols + 1, col=numero % cols + 1)
    _subtitulos_pequenos(fig)
    return _estilo(fig, "Distribucion de las variables numericas", alto=240 * filas + 80)


def grafico_boxplots(df, resultado_outliers):
    if resultado_outliers["omitido"]:
        return None
    tabla = resultado_outliers["tablas"]["por_columna"]
    columnas = tabla[tabla["iqr_n"] > 0]["columna"].head(config.MAX_BOXPLOTS).tolist()
    if not columnas:
        return None
    filas, cols = _cuadricula(len(columnas), 4)
    fig = make_subplots(rows=filas, cols=cols, subplot_titles=columnas,
                        vertical_spacing=0.14, horizontal_spacing=0.06)
    for numero, col in enumerate(columnas):
        fig.add_trace(go.Box(
            y=df[col].tolist(), boxpoints="outliers", name=col,
            line=dict(color=AZUL, width=1.5), fillcolor="rgba(42,120,214,0.18)",
            marker=dict(color=NARANJA, size=6),
        ), row=numero // cols + 1, col=numero % cols + 1)
    fig.update_xaxes(showticklabels=False)
    _subtitulos_pequenos(fig)
    return _estilo(fig, "Valores atipicos por variable (puntos naranja = fuera de la caja)",
                   alto=300 * filas + 80)


def grafico_categoricas(df, esquema):
    columnas = columnas_por_tipo(esquema, "categorica", "booleana")[:config.MAX_CATEGORICAS]
    if not columnas:
        return None
    filas, cols = _cuadricula(len(columnas), 3)
    fig = make_subplots(rows=filas, cols=cols, subplot_titles=columnas,
                        vertical_spacing=0.14, horizontal_spacing=0.12)
    for numero, col in enumerate(columnas):
        frecuencias = df[col].value_counts().head(config.TOP_CATEGORIAS)
        porcentajes = frecuencias / len(df) * 100
        fig.add_trace(go.Bar(
            x=porcentajes.tolist(), y=[str(v) for v in frecuencias.index], orientation="h",
            marker=dict(color=AZUL, line=dict(color=SUPERFICIE, width=1)),
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ), row=numero // cols + 1, col=numero % cols + 1)
    fig.update_yaxes(autorange="reversed")
    _subtitulos_pequenos(fig)
    return _estilo(fig, "Categorias mas frecuentes (% de registros)", alto=260 * filas + 80)


def grafico_temporal(df, esquema):
    fechas = columnas_por_tipo(esquema, "temporal")
    if not fechas:
        return None
    col = fechas[0]
    rango = (df[col].max() - df[col].min()).days
    frecuencia = "MS" if rango >= 180 else ("W" if rango >= 21 else "D")
    serie = df.set_index(col).resample(frecuencia).size()
    fig = go.Figure(go.Scatter(
        x=serie.index.tolist(), y=serie.tolist(),
        mode="lines+markers" if len(serie) <= 30 else "lines",
        line=dict(color=AZUL, width=2), marker=dict(size=8, color=AZUL),
        hovertemplate="%{x|%d/%m/%Y}: %{y} registros<extra></extra>",
    ))
    fig.update_yaxes(title="Registros", rangemode="tozero")
    return _estilo(fig, f"Registros a lo largo del tiempo ({col})", alto=360)



def grafico_outliers_pca(resultado_outliers, resultado_clustering):
    if resultado_outliers["omitido"] or resultado_clustering["omitido"]:
        return None
    coordenadas = resultado_clustering["datos_graficos"]["pca"]
    es_outlier = resultado_outliers["datos_graficos"]["marcas"]["es_outlier"]

    fig = go.Figure()
    grupos = [("Normales", ~es_outlier, AZUL, "circle", 0.55),
              ("Outliers", es_outlier, NARANJA, "diamond", 0.95)]
    for nombre, mascara, color, simbolo, opacidad in grupos:
        puntos = coordenadas[mascara]
        fig.add_trace(go.Scatter(
            x=puntos["pc1"].tolist(), y=puntos["pc2"].tolist(), mode="markers",
            name=f"{nombre} ({int(mascara.sum())})", customdata=puntos.index.tolist(),
            marker=dict(color=color, symbol=simbolo, size=8, opacity=opacidad,
                        line=dict(color=SUPERFICIE, width=1)),
            hovertemplate="fila %{customdata}<extra>" + nombre + "</extra>",
        ))
    varianza = resultado_clustering["datos_graficos"]["varianza_pca"]
    fig.update_xaxes(title=f"Componente 1 ({varianza[0]}% de la variacion)")
    fig.update_yaxes(title=f"Componente 2 ({varianza[1]}% de la variacion)")
    return _estilo(fig, "Outliers detectados (vista en 2 dimensiones)", alto=480, leyenda=True)


def grafico_clusters_pca(resultado_clustering):
    if resultado_clustering["omitido"]:
        return None
    datos = resultado_clustering["datos_graficos"]
    coordenadas = datos["pca"]
    etiquetas = datos["etiquetas"]["cluster_kmeans"]


    agrupados = coordenadas[etiquetas != -1]
    margen_x = (agrupados["pc1"].max() - agrupados["pc1"].min()) * 0.12
    margen_y = (agrupados["pc2"].max() - agrupados["pc2"].min()) * 0.12
    rango_x = [agrupados["pc1"].min() - margen_x, agrupados["pc1"].max() + margen_x]
    rango_y = [agrupados["pc2"].min() - margen_y, agrupados["pc2"].max() + margen_y]

    fig = go.Figure()
    for cluster in sorted(etiquetas.unique()):
        puntos = coordenadas[etiquetas == cluster]
        if cluster == -1:
            fuera = int(((puntos["pc1"] < rango_x[0]) | (puntos["pc1"] > rango_x[1])
                         | (puntos["pc2"] < rango_y[0]) | (puntos["pc2"] > rango_y[1])).sum())
            nombre = f"Excluidos como outliers ({len(puntos)})"
            if fuera:
                nombre += f", {fuera} fuera de la vista"
            color, simbolo = APAGADO, "x"
        else:
            nombre = f"Cluster {cluster} ({len(puntos)})"
            color = COLORES[cluster % len(COLORES)]
            simbolo = SIMBOLOS[cluster % len(SIMBOLOS)]
        fig.add_trace(go.Scatter(
            x=puntos["pc1"].tolist(), y=puntos["pc2"].tolist(), mode="markers",
            name=nombre, customdata=puntos.index.tolist(),
            marker=dict(color=color, symbol=simbolo, size=8, opacity=0.8,
                        line=dict(color=SUPERFICIE, width=1)),
            hovertemplate="fila %{customdata}<extra>" + nombre + "</extra>",
        ))
    varianza = datos["varianza_pca"]
    fig.update_xaxes(title=f"Componente 1 ({varianza[0]}% de la variacion)", range=rango_x)
    fig.update_yaxes(title=f"Componente 2 ({varianza[1]}% de la variacion)", range=rango_y)
    return _estilo(fig, f"Grupos encontrados por K-means (k = {datos['k_elegido']})",
                   alto=500, leyenda=True)


def grafico_silhouette(resultado_clustering):
    if resultado_clustering["omitido"]:
        return None
    datos = resultado_clustering["datos_graficos"]
    tabla = datos["silhouette_por_k"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("Silhouette (mas alto = mejor)",
                                        "Inercia (busca el codo)"))
    for columna, posicion in (("silhouette", 1), ("inercia", 2)):
        fig.add_trace(go.Scatter(
            x=tabla["k"].tolist(), y=tabla[columna].tolist(), mode="lines+markers",
            line=dict(color=AZUL, width=2), marker=dict(size=8, color=AZUL),
            hovertemplate="k=%{x}: %{y:.3f}<extra></extra>",
        ), row=1, col=posicion)
    elegido = tabla[tabla["k"] == datos["k_elegido"]].iloc[0]
    fig.add_trace(go.Scatter(
        x=[datos["k_elegido"]], y=[elegido["silhouette"]], mode="markers+text",
        marker=dict(size=13, color=NARANJA, line=dict(color=SUPERFICIE, width=2)),
        text=[f"  k elegido = {datos['k_elegido']}"], textposition="middle right",
        hoverinfo="skip",
    ), row=1, col=1)
    fig.update_xaxes(title="k (numero de grupos)", dtick=1)
    _subtitulos_pequenos(fig)
    return _estilo(fig, "Como se eligio el numero de grupos", alto=380)


def grafico_perfiles_clusters(resultado_clustering):
    if resultado_clustering["omitido"]:
        return None
    diferencias = resultado_clustering["datos_graficos"]["diferencias"]
    mas_distintivas = diferencias.abs().max().sort_values(ascending=False)
    columnas = mas_distintivas.head(config.MAX_VARIABLES_HEATMAP).index.tolist()
    matriz = diferencias[columnas]

    fig = go.Figure(go.Heatmap(
        z=matriz.to_numpy(), x=columnas, y=[f"Cluster {c}" for c in matriz.index],
        zmin=-2, zmax=2, colorscale=DIVERGENTE,
        colorbar=dict(title="Desv. est.", thickness=12),
        hovertemplate="%{y} - %{x}: %{z:.2f} desv. est.<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    return _estilo(fig, "Que distingue a cada cluster (azul = bajo, rojo = alto)",
                   alto=max(300, 70 * len(matriz) + 180))



def grafico_heatmap_correlaciones(resultado_corr):
    matriz = resultado_corr["datos_graficos"].get("matriz_pearson")
    if matriz is None:
        return None
    if len(matriz) > config.MAX_VARIABLES_HEATMAP:
        conectividad = matriz.abs().sum() - 1  
        elegidas = conectividad.sort_values(ascending=False).head(config.MAX_VARIABLES_HEATMAP)
        matriz = matriz.loc[elegidas.index, elegidas.index]
    nombres = matriz.columns.tolist()

    fig = go.Figure(go.Heatmap(
        z=matriz.to_numpy(), x=nombres, y=nombres, zmin=-1, zmax=1, zmid=0,
        colorscale=DIVERGENTE, colorbar=dict(title="r", thickness=12),
        text=matriz.round(2).to_numpy() if len(nombres) <= 12 else None,
        texttemplate="%{text}" if len(nombres) <= 12 else None,
        hovertemplate="%{y} vs %{x}: r = %{z:.2f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    return _estilo(fig, "Correlacion entre variables numericas (Pearson)",
                   alto=max(450, 26 * len(nombres) + 160))


def grafico_dispersion_pares(df, resultado_corr):
    pares = resultado_corr["tablas"].get("pares_numericos")
    if pares is None or pares.empty:
        return None
    pares = pares.head(config.MAX_DISPERSIONES)
    filas, cols = _cuadricula(len(pares), 2)
    titulos = [f"{f.variable_a} vs {f.variable_b} (r = {f.pearson:.2f})"
               for f in pares.itertuples()]
    fig = make_subplots(rows=filas, cols=cols, subplot_titles=titulos,
                        vertical_spacing=0.16, horizontal_spacing=0.1)
    for numero, f in enumerate(pares.itertuples()):
        fig.add_trace(go.Scatter(
            x=df[f.variable_a].tolist(), y=df[f.variable_b].tolist(), mode="markers",
            marker=dict(color=AZUL, size=7, opacity=0.6, line=dict(color=SUPERFICIE, width=1)),
            hovertemplate=f"{f.variable_a}: %{{x}}<br>{f.variable_b}: %{{y}}<extra></extra>",
        ), row=numero // cols + 1, col=numero % cols + 1)
        fig.update_xaxes(title=f.variable_a, row=numero // cols + 1, col=numero % cols + 1)
        fig.update_yaxes(title=f.variable_b, row=numero // cols + 1, col=numero % cols + 1)
    _subtitulos_pequenos(fig)
    return _estilo(fig, "Pares de variables mas correlacionados", alto=380 * filas + 60)


def grafico_relaciones(resultado_corr):
    ranking = resultado_corr["tablas"].get("ranking")
    if ranking is None or ranking.empty:
        return None
    tipos = [t for t in ["numerica-numerica", "categorica-numerica", "categorica-categorica"]
             if t in set(ranking["tipo"])]
    titulos = {"numerica-numerica": "Numerica vs numerica (Pearson r)",
               "categorica-numerica": "Categorica vs numerica (eta cuadrado ajustado)",
               "categorica-categorica": "Categorica vs categorica (V de Cramer)"}
    fig = make_subplots(rows=len(tipos), cols=1, subplot_titles=[titulos[t] for t in tipos],
                        vertical_spacing=0.18)
    for numero, tipo in enumerate(tipos):
        seccion = ranking[ranking["tipo"] == tipo].head(6)
        etiquetas = [f"{a} vs {b}" for a, b in zip(seccion["variable_a"], seccion["variable_b"])]
        fig.add_trace(go.Bar(
            x=seccion["valor"].abs().tolist(), y=etiquetas, orientation="h",
            text=[f"{v:.2f}" for v in seccion["valor"].abs()], textposition="outside",
            cliponaxis=False,
            marker=dict(color=COLORES[numero], line=dict(color=SUPERFICIE, width=1)),
            hovertemplate="%{y}: %{x:.2f}<extra></extra>",
        ), row=numero + 1, col=1)
        fig.update_yaxes(autorange="reversed", row=numero + 1, col=1)
        fig.update_xaxes(range=[0, 1], row=numero + 1, col=1)
    _subtitulos_pequenos(fig)
    fig.update_layout(bargap=0.4)
    return _estilo(fig, "Relaciones mas importantes entre variables", alto=270 * len(tipos) + 60)



def generar_figuras(df, esquema, log_limpieza, resultados_ia):
    outliers = resultados_ia["outliers"]
    clustering = resultados_ia["clustering"]
    correlaciones = resultados_ia["correlaciones"]

    candidatas = {
        "nulos": grafico_nulos(log_limpieza),
        "histogramas": grafico_histogramas(df, esquema),
        "categoricas": grafico_categoricas(df, esquema),
        "temporal": grafico_temporal(df, esquema),
        "boxplots": grafico_boxplots(df, outliers),
        "outliers_pca": grafico_outliers_pca(outliers, clustering),
        "clusters_pca": grafico_clusters_pca(clustering),
        "silhouette": grafico_silhouette(clustering),
        "perfiles_clusters": grafico_perfiles_clusters(clustering),
        "heatmap_correlaciones": (None if correlaciones["omitido"]
                                  else grafico_heatmap_correlaciones(correlaciones)),
        "dispersion_pares": (None if correlaciones["omitido"]
                             else grafico_dispersion_pares(df, correlaciones)),
        "relaciones": (None if correlaciones["omitido"]
                       else grafico_relaciones(correlaciones)),
    }
    return {nombre: fig for nombre, fig in candidatas.items() if fig is not None}