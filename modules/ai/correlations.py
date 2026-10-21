# Correlaciones y dependencia entre variables

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

from modules import config
from modules.ai.base import resultado_base
from modules.type_detector import columnas_por_tipo


def clasificar_fuerza(valor, fuerte, moderada):
    magnitud = abs(valor)
    if magnitud >= fuerte:
        return "fuerte"
    if magnitud >= moderada:
        return "moderada"
    return "debil"

# numerica vs numerica
def correlaciones_numericas(df, columnas):
    n = len(df)
    pearson = df[columnas].corr(method="pearson")
    spearman = df[columnas].corr(method="spearman")

    i, j = np.triu_indices(len(columnas), k=1)
    nombres = np.array(columnas)
    tabla = pd.DataFrame({
        "variable_a": nombres[i],
        "variable_b": nombres[j],
        "pearson": pearson.to_numpy()[i, j],
        "spearman": spearman.to_numpy()[i, j],
    }).dropna()

    r = tabla["pearson"].to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        t = r * np.sqrt((n - 2) / (1 - r ** 2))
    p = 2 * stats.t.sf(np.abs(t), n - 2)
    p[np.abs(r) >= 1] = 0.0
    tabla["p_valor"] = p

    tabla = tabla[tabla["pearson"].abs() >= config.CORR_MODERADA].copy()
    tabla["fuerza"] = [clasificar_fuerza(v, config.CORR_FUERTE, config.CORR_MODERADA)
                       for v in tabla["pearson"]]
    tabla["multicolinealidad"] = tabla["pearson"].abs() >= config.CORR_MULTICOLINEALIDAD
    tabla["posible_no_lineal"] = (tabla["spearman"].abs() - tabla["pearson"].abs()) >= 0.15
    tabla = tabla.sort_values("pearson", key=abs, ascending=False).reset_index(drop=True)
    return pearson, spearman, tabla

# categorica vs numerica 
def dependencia_cat_num(df, cols_cat, cols_num):
    n = len(df)
    datos = df[cols_num]
    media_global = datos.mean().to_numpy()
    ss_total = ((datos - datos.mean()) ** 2).sum().to_numpy()

    filas = []
    for cat in cols_cat:
        grupos = df.groupby(cat)
        k = grupos.ngroups
        if k < 2 or n <= k:
            continue
        medias = grupos[cols_num].mean().to_numpy()
        tamanos = grupos.size().to_numpy()
        ss_entre = (tamanos[:, None] * (medias - media_global) ** 2).sum(axis=0)

        with np.errstate(divide="ignore", invalid="ignore"):
            ss_dentro = ss_total - ss_entre
            cuadrado_medio_dentro = ss_dentro / (n - k)
            f = (ss_entre / (k - 1)) / cuadrado_medio_dentro
            eta2 = (ss_entre - (k - 1) * cuadrado_medio_dentro) / (ss_total + cuadrado_medio_dentro)
        eta2 = np.clip(eta2, 0, None)       
        p = stats.f.sf(f, k - 1, n - k)
        for num, e, pv in zip(cols_num, eta2, p):
            if np.isfinite(e):
                filas.append({"categorica": cat, "numerica": num,
                              "eta2": float(e), "p_valor": float(pv)})

    tabla = pd.DataFrame(filas, columns=["categorica", "numerica", "eta2", "p_valor"])
    if tabla.empty:
        return tabla
    tabla["fuerza"] = [clasificar_fuerza(v, config.ETA_FUERTE, config.ETA_MODERADA)
                       for v in tabla["eta2"]]
    return tabla.sort_values("eta2", ascending=False).reset_index(drop=True)

# categorica vs categorica 
def cramer_v(tabla_contingencia):
    chi2, p, _, esperados = stats.chi2_contingency(tabla_contingencia, correction=False)
    n = tabla_contingencia.to_numpy().sum()
    filas, columnas = tabla_contingencia.shape
    phi2 = max(0.0, chi2 / n - (columnas - 1) * (filas - 1) / (n - 1))
    filas_corr = filas - (filas - 1) ** 2 / (n - 1)
    columnas_corr = columnas - (columnas - 1) ** 2 / (n - 1)
    divisor = min(columnas_corr - 1, filas_corr - 1)
    v = float(np.sqrt(phi2 / divisor)) if divisor > 0 else 0.0
    return v, float(p), float(esperados.mean())

def dependencia_cat_cat(df, cols_cat):
    filas = []
    for a, b in combinations(cols_cat, 2):
        tabla = pd.crosstab(df[a], df[b])
        if min(tabla.shape) < 2:
            continue
        v, p, esperado = cramer_v(tabla)
        if esperado < config.MIN_ESPERADO_CHI2:
            continue  
        filas.append({"variable_a": a, "variable_b": b, "cramer_v": v, "p_valor": p})

    tabla = pd.DataFrame(filas, columns=["variable_a", "variable_b", "cramer_v", "p_valor"])
    if tabla.empty:
        return tabla
    tabla["fuerza"] = [clasificar_fuerza(v, config.CRAMER_FUERTE, config.CRAMER_MODERADO)
                       for v in tabla["cramer_v"]]
    return tabla.sort_values("cramer_v", ascending=False).reset_index(drop=True)

# Ranking global
def construir_ranking(pares_num, cat_num, cat_cat):
    filas = []
    for _, f in pares_num.iterrows():
        filas.append({"tipo": "numerica-numerica", "variable_a": f["variable_a"],
                      "variable_b": f["variable_b"], "medida": "Pearson r",
                      "valor": f["pearson"], "p_valor": f["p_valor"], "fuerza": f["fuerza"]})
    for _, f in cat_num.iterrows():
        filas.append({"tipo": "categorica-numerica", "variable_a": f["categorica"],
                      "variable_b": f["numerica"], "medida": "eta cuadrado ajustado",
                      "valor": f["eta2"], "p_valor": f["p_valor"], "fuerza": f["fuerza"]})
    for _, f in cat_cat.iterrows():
        filas.append({"tipo": "categorica-categorica", "variable_a": f["variable_a"],
                      "variable_b": f["variable_b"], "medida": "V de Cramer",
                      "valor": f["cramer_v"], "p_valor": f["p_valor"], "fuerza": f["fuerza"]})

    ranking = pd.DataFrame(filas, columns=["tipo", "variable_a", "variable_b", "medida",
                                           "valor", "p_valor", "fuerza"])
    ranking = ranking[(ranking["p_valor"] < config.P_MAXIMO) & (ranking["fuerza"] != "debil")]

    ranking["orden"] = ranking["fuerza"].replace({"fuerte": 0, "moderada": 1})
    ranking["magnitud"] = ranking["valor"].abs()
    ranking = ranking.sort_values(["orden", "magnitud"], ascending=[True, False])
    return ranking.drop(columns=["orden", "magnitud"]).head(config.MAX_RELACIONES).reset_index(drop=True)

# Funcion principal del modulo
def analizar_correlaciones(df, esquema):
    """Calcula todas las correlaciones y dependencias posibles segun los tipos."""
    cols_num = columnas_por_tipo(esquema, "numerica")
    cols_cat = columnas_por_tipo(esquema, "categorica", "booleana")

    if len(cols_num) < 2 and len(cols_cat) < 2 and not (cols_num and cols_cat):
        return resultado_base(
            True, "No hay suficientes variables para calcular relaciones.")

    resultado = resultado_base()
    pares_num = pd.DataFrame()
    cat_num = pd.DataFrame()
    cat_cat = pd.DataFrame()
    datos_graficos = {}

    if len(cols_num) >= 2:
        pearson, spearman, pares_num = correlaciones_numericas(df, cols_num)
        datos_graficos["matriz_pearson"] = pearson
        datos_graficos["matriz_spearman"] = spearman
    else:
        resultado["advertencias"].append(
            "Hay menos de 2 columnas numericas: no se calcularon correlaciones numericas.")

    if cols_cat and cols_num:
        cat_num = dependencia_cat_num(df, cols_cat, cols_num)
    if len(cols_cat) >= 2:
        cat_cat = dependencia_cat_cat(df, cols_cat)

    ranking = construir_ranking(pares_num, cat_num, cat_cat)

    resultado["resumen"] = {
        "pares_numericos_fuertes": int((pares_num["fuerza"] == "fuerte").sum())
        if not pares_num.empty else 0,
        "pares_multicolinealidad": int(pares_num["multicolinealidad"].sum())
        if not pares_num.empty else 0,
        "relaciones_cat_num_significativas": int(
            ((cat_num["p_valor"] < config.P_MAXIMO) & (cat_num["fuerza"] != "debil")).sum())
        if not cat_num.empty else 0,
        "relaciones_cat_cat_significativas": int(
            ((cat_cat["p_valor"] < config.P_MAXIMO) & (cat_cat["fuerza"] != "debil")).sum())
        if not cat_cat.empty else 0,
    }
    resultado["tablas"] = {
        "pares_numericos": pares_num.head(config.MAX_PARES_TABLA),
        "categorica_numerica": cat_num.head(config.MAX_PARES_TABLA),
        "categorica_categorica": cat_cat.head(config.MAX_PARES_TABLA),
        "ranking": ranking,
    }
    resultado["datos_graficos"] = datos_graficos

    if resultado["resumen"]["pares_multicolinealidad"] > 0:
        resultado["advertencias"].append(
            f"{resultado['resumen']['pares_multicolinealidad']} par(es) de variables tienen "
            f"correlacion superior a {config.CORR_MULTICOLINEALIDAD}: miden casi lo mismo "
            "(multicolinealidad).")
    return resultado