from modules import config

ORDEN_NIVEL = {"alto": 0, "medio": 1, "bajo": 2}

def _hallazgo(categoria, nivel, titulo, detalle=""):
    return {"categoria": categoria, "nivel": nivel, "titulo": titulo, "detalle": detalle}

def _lista(nombres, maximo=4):
    nombres = [str(n) for n in nombres]
    texto = ", ".join(nombres[:maximo])
    if len(nombres) > maximo:
        texto += f" y {len(nombres) - maximo} más"
    return texto

def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"

def _pct(valor):
    return f"{valor:.0f}%" if float(valor).is_integer() else f"{valor:.1f}%"

# Calidad de datos
def hallazgos_calidad(log, esquema, estadisticas):
    resultado = []
    filas, columnas = log["filas_finales"], log["columnas_finales"]
    resultado.append(_hallazgo(
        "calidad", "bajo", f"Se analizaron {filas} filas y {columnas} columnas",
        f"El archivo original tenía {log['filas_originales']} filas y "
        f"{log['columnas_originales']} columnas."))

    duplicados = log.get("duplicados_eliminados", 0)
    if duplicados > 0:
        porcentaje = duplicados / log["filas_originales"] * 100
        resultado.append(_hallazgo(
            "calidad", "alto" if porcentaje >= 5 else "medio",
            f"Se {'eliminó' if duplicados == 1 else 'eliminaron'} {_plural(duplicados, 'fila duplicada', 'filas duplicadas')} ({_pct(porcentaje)})",
            "Las filas repetidas se quitaron para que no pesen doble en el análisis."))
    
    for columna, cambios in log.get("categorias_unificadas", {}).items():
        ejemplos = "; ".join(f"«{o}» → «{d}»" for o, d in list(cambios.items())[:3])
        resultado.append(_hallazgo(
            "calidad", "medio",
            f"En «{columna}» se unificaron {_plural(len(cambios), 'nombre', 'nombres')} escritos de forma distinta",
            f"Ejemplos: {ejemplos}. Se agruparon por mayúsculas, tildes, puntuación y sufijos "
            "como FC, y se conservó la forma más frecuente."))

    for columna, pares in log.get("posibles_duplicados", {}).items():
        ejemplos = "; ".join(f"«{a}» y «{b}»" for a, b in pares[:3])
        resultado.append(_hallazgo(
            "calidad", "medio",
            f"En «{columna}» podría haber nombres repetidos que no se unificaron",
            f"Ejemplos: {ejemplos}. Si son lo mismo, conviene corregirlos en el archivo original: "
            "mientras tanto, los análisis por esta columna quedan divididos."))
    eliminadas = log.get("columnas_eliminadas_por_nulos", [])
    if eliminadas:
        resultado.append(_hallazgo(
            "calidad", "medio",
            f"Se descartaron {len(eliminadas)} columnas por tener demasiados vacíos",
            f"Tenían más de {config.MAX_NULOS_COLUMNA * 100:.0f}% de datos faltantes: "
            f"{_lista(eliminadas)}."))

    nulos = log.get("nulos_por_columna", {})
    imputadas = {c: v["porcentaje"] for c, v in nulos.items()
                 if c in log.get("imputaciones", {}) and v["porcentaje"] >= config.NULOS_NOTABLES}
    if imputadas:
        peor = max(imputadas, key=imputadas.get)
        grave = imputadas[peor] >= config.NULOS_GRAVES
        resultado.append(_hallazgo(
            "calidad", "alto" if grave else "medio",
            f"{_plural(len(imputadas), 'columna tenía', 'columnas tenían')} {config.NULOS_NOTABLES}% o más de datos faltantes",
            f"La más afectada es «{peor}» con {_pct(imputadas[peor])}. Los vacíos se rellenaron "
            "con la mediana (números) o la moda (categorías), lo que puede suavizar la variación real."))

    excluidas = estadisticas.get("excluidas", {})
    if excluidas:
        resultado.append(_hallazgo(
            "calidad", "bajo", f"{_plural(len(excluidas), 'columna no entra', 'columnas no entran')} al análisis estadístico",
            "Son identificadores, textos libres o columnas con un solo valor: "
            + _lista([f"{c} ({t})" for c, t in excluidas.items()]) + "."))
    return resultado

# Estadistica descriptiva

def hallazgos_descriptivos(estadisticas):
    resultado = []

    numericas = estadisticas["numericas"]
    if not numericas.empty:
        sesgadas = numericas[numericas["asimetria"].abs() > config.ASIMETRIA_ALTA]
        if len(sesgadas) > 0:
            resultado.append(_hallazgo(
                "descriptivo", "medio",
                (f"1 de {len(numericas)} variables numéricas está muy sesgada" if len(sesgadas) == 1
                 else f"{len(sesgadas)} de {len(numericas)} variables numéricas están muy sesgadas"),
                f"Ejemplos: {_lista(sesgadas.index.tolist())}. Cuando hay sesgo, la mediana "
                "describe mejor al dato típico que la media, y el Z-score es menos confiable."))

    for columna, info in estadisticas["categoricas"].items():
        principal = info["top"].iloc[0]
        if principal["porcentaje"] >= config.DOMINANCIA_CATEGORIA:
            resultado.append(_hallazgo(
                "descriptivo", "medio",
                f"En «{columna}», {_pct(principal['porcentaje'])} de los registros son «{principal['valor']}»",
                "Una categoría tan dominante aporta poca información para distinguir registros."))

    for columna, info in estadisticas["temporales"].items():
        resultado.append(_hallazgo(
            "descriptivo", "bajo", f"«{columna}» cubre {info['rango_dias']} días",
            f"Va del {info['minimo']:%d/%m/%Y} al {info['maximo']:%d/%m/%Y}."))
    return resultado

# Outliers

def hallazgos_outliers(outliers):
    if outliers["omitido"]:
        return [_hallazgo("outliers", "bajo", "No se buscaron valores atípicos", outliers["motivo"])]

    resumen = outliers["resumen"]
    if resumen["n_outliers"] == 0:
        return [_hallazgo(
            "outliers", "bajo", "No se confirmaron valores atípicos",
            "Isolation Forest no encontró registros raros que además Z-score o IQR confirmaran.")]

    detalle = (f"Isolation Forest los marcó como raros y Z-score o IQR lo confirmaron en alguna columna. "
               f"Las columnas más afectadas son {_lista(resumen['columnas_mas_afectadas'])}.")
    registros = outliers["tablas"]["registros"]
    if not registros.empty:
        peor = registros.iloc[0]
        valor = peor["valor"]
        valor = f"{valor:.4g}" if isinstance(valor, float) else str(valor)
        detalle += (f" El más extremo es la fila {peor['fila']}: «{peor['variable_mas_extrema']}» "
                    f"vale {valor} ({peor['z_maximo']} desviaciones de la media).")
    detalle += " Un valor atípico no siempre es un error: puede ser un caso real e interesante."

    resultado = [_hallazgo(
        "outliers", "alto" if resumen["pct_outliers"] >= 8 else "medio",
        f"{_plural(resumen['n_outliers'], 'registro atípico', 'registros atípicos')} ({_pct(resumen['pct_outliers'])})", detalle)]
    for aviso in outliers["advertencias"]:
        resultado.append(_hallazgo("outliers", "bajo", "Límite del método IQR", aviso))
    return resultado

# Clustering

def _describir_grupos(clustering):
    tamanos = clustering["tablas"]["tamanos"]
    distintivas = clustering["tablas"]["distintivas"]
    frases = []
    for fila in tamanos.head(4).itertuples():
        propias = distintivas[distintivas["cluster"] == fila.cluster].head(2)
        rasgos = ", ".join(f"{r.variable} {r.direccion}" for r in propias.itertuples())
        frases.append(f"Grupo {fila.cluster} ({_pct(fila.porcentaje)}): {rasgos}")
    return "; ".join(frases)


def hallazgos_clustering(clustering):
    if clustering["omitido"]:
        return [_hallazgo("clustering", "bajo", "No se formaron grupos", clustering["motivo"])]

    r = clustering["resumen"]
    silhouette = r["kmeans_silhouette"]
    nivel = "alto" if silhouette >= 0.5 and not r["datos_discretos"] else "medio"
    interpretacion = ("datos muy repetidos: interpretar con cuidado" if r["datos_discretos"]
                      else r["kmeans_interpretacion"])
    titulo = f"K-means encontró {r['kmeans_k']} grupos ({interpretacion})"
    detalle = f"Silhouette = {silhouette}. " + _describir_grupos(clustering) + "."
    if silhouette < 0.25:
        detalle += (" Un silhouette tan bajo indica que los registros no forman grupos claros: "
                    "no conviene sacar conclusiones fuertes de estos grupos.")
    if r["datos_discretos"]:
        detalle += (f" Ojo: hay solo {r['combinaciones_unicas']} combinaciones distintas de valores, "
                    "así que los grupos reflejan combinaciones repetidas y el silhouette puede "
                    "salir inflado.")
    resultado = [_hallazgo("clustering", nivel, titulo, detalle)]

    if r["dbscan_grupos"] <= 1:
        resultado.append(_hallazgo(
            "clustering", "bajo", "DBSCAN no separó grupos por densidad",
            f"Encontró {r['dbscan_grupos']} grupo y {r['dbscan_ruido']} puntos aislados (ruido): "
            "los datos forman una sola nube densa."))
    else:
        resultado.append(_hallazgo(
            "clustering", "bajo", f"DBSCAN encontró {r['dbscan_grupos']} zonas densas",
            f"Además dejó {r['dbscan_ruido']} puntos como ruido (no pertenecen a ninguna zona)."))

    if r["varianza_explicada_pca"] < 50:
        resultado.append(_hallazgo(
            "clustering", "bajo", "El gráfico de grupos en 2D es una vista aproximada",
            f"Las 2 dimensiones del gráfico conservan solo {r['varianza_explicada_pca']}% de la "
            "variación original."))
    return resultado

# Correlaciones

def hallazgos_correlaciones(correlaciones):
    if correlaciones["omitido"]:
        return [_hallazgo("correlaciones", "bajo", "No se calcularon relaciones", correlaciones["motivo"])]

    resultado = []
    tablas = correlaciones["tablas"]

    pares = tablas["pares_numericos"]
    fuertes = pares[pares["fuerza"] == "fuerte"] if not pares.empty else pares
    if not fuertes.empty:
        primero = fuertes.iloc[0]
        resultado.append(_hallazgo(
            "correlaciones", "alto",
            f"«{primero['variable_a']}» y «{primero['variable_b']}» están muy relacionadas (r = {primero['pearson']:.2f})",
            f"Cuando una sube, la otra tiende a {'subir' if primero['pearson'] > 0 else 'bajar'}. "
            f"En total hay {len(fuertes)} pares de variables numéricas con relación fuerte (|r| ≥ {config.CORR_FUERTE})."))
    elif not pares.empty:
        resultado.append(_hallazgo(
            "correlaciones", "medio", f"Hay {len(pares)} pares numéricos con relación moderada",
            f"La más alta es «{pares.iloc[0]['variable_a']}» con «{pares.iloc[0]['variable_b']}» "
            f"(r = {pares.iloc[0]['pearson']:.2f})."))

    multi = correlaciones["resumen"]["pares_multicolinealidad"]
    if multi > 0:
        resultado.append(_hallazgo(
            "correlaciones", "medio",
            (f"1 par de variables mide casi lo mismo" if multi == 1 else f"{multi} pares de variables miden casi lo mismo")
            + f" (|r| ≥ {config.CORR_MULTICOLINEALIDAD})",
            "Es multicolinealidad: son variables redundantes. Antes de construir un modelo "
            "conviene quedarse con una de cada par."))

    no_lineales = pares[pares["posible_no_lineal"]] if not pares.empty else pares
    if not no_lineales.empty:
        f = no_lineales.iloc[0]
        resultado.append(_hallazgo(
            "correlaciones", "bajo",
            f"«{f['variable_a']}» y «{f['variable_b']}» podrían tener una relación no lineal",
            f"Spearman ({f['spearman']:.2f}) es bastante mayor que Pearson ({f['pearson']:.2f})."))

    cat_num = tablas["categorica_numerica"]
    if not cat_num.empty:
        cat_num = cat_num[(cat_num["p_valor"] < config.P_MAXIMO) & (cat_num["fuerza"] != "debil")]
    for f in cat_num.head(2).itertuples():
        resultado.append(_hallazgo(
            "correlaciones", "alto" if f.fuerza == "fuerte" else "medio",
            f"«{f.categorica}» explica {_pct(f.eta2 * 100)} de la variación de «{f.numerica}»",
            f"Relación {f.fuerza} (eta cuadrado ajustado = {f.eta2:.2f}). Revisa que una columna "
            "no se derive de la otra: entonces la relación sería obvia."))

    cat_cat = tablas["categorica_categorica"]
    if not cat_cat.empty:
        cat_cat = cat_cat[(cat_cat["p_valor"] < config.P_MAXIMO) & (cat_cat["fuerza"] != "debil")]
    if not cat_cat.empty:
        f = cat_cat.iloc[0]
        resultado.append(_hallazgo(
            "correlaciones", "alto" if f["fuerza"] == "fuerte" else "medio",
            f"«{f['variable_a']}» y «{f['variable_b']}» están asociadas (V de Cramér = {f['cramer_v']:.2f})",
            f"Hay {len(cat_cat)} pares de categorías con asociación significativa."))
    return resultado

# Funcion principal del modulo

def generar_hallazgos(log, esquema, estadisticas, resultados_ia):
    
    todos = (hallazgos_calidad(log, esquema, estadisticas)
             + hallazgos_descriptivos(estadisticas)
             + hallazgos_outliers(resultados_ia["outliers"])
             + hallazgos_clustering(resultados_ia["clustering"])
             + hallazgos_correlaciones(resultados_ia["correlaciones"]))
    ordenados = sorted(todos, key=lambda h: ORDEN_NIVEL[h["nivel"]])
    return ordenados[:config.MAX_HALLAZGOS]