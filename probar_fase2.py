"""
Prueba rapida de la capa de IA y los graficos.
Uso (desde la raiz del proyecto):
    python probar_fase2.py data/ejemplo_ventas.csv
Genera output/prueba_fase2.html y lo abre en el navegador.
"""

import os
import sys
import webbrowser

import pandas as pd

from modules.ai.clustering import agrupar
from modules.ai.correlations import analizar_correlaciones
from modules.ai.outliers import detectar_outliers
from modules.cleaner import limpiar
from modules.loader import ErrorDeCarga, cargar_archivo
from modules.type_detector import detectar_tipos
from modules.viz import generar_figuras

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

ruta = sys.argv[1] if len(sys.argv) > 1 else "data/ejemplo_ventas.csv"
hoja = sys.argv[2] if len(sys.argv) > 2 else None

# ---- fase 1: cargar, limpiar y detectar tipos ----
try:
    df, metadata = cargar_archivo(ruta, hoja)
except ErrorDeCarga as error:
    print(f"ERROR: {error}")
    sys.exit(1)
df, log = limpiar(df)
esquema = detectar_tipos(df)

# ---- fase 2: capa de IA ----
outliers = detectar_outliers(df, esquema)

# los outliers se dejan fuera del clustering para que no deformen los grupos
mascara = None if outliers["omitido"] else outliers["datos_graficos"]["marcas"]["es_outlier"]
clustering = agrupar(df, esquema, mascara)
correlaciones = analizar_correlaciones(df, esquema)

for nombre, resultado in [("OUTLIERS", outliers), ("CLUSTERING", clustering),
                          ("CORRELACIONES", correlaciones)]:
    print(f"\n=== {nombre} ===")
    if resultado["omitido"]:
        print("Omitido:", resultado["motivo"])
        continue
    for clave, valor in resultado["resumen"].items():
        print(f"{clave}: {valor}")
    for aviso in resultado["advertencias"]:
        print("AVISO:", aviso)

if not outliers["omitido"]:
    print("\nRegistros mas atipicos:")
    print(outliers["tablas"]["registros"].to_string(index=False))
if not clustering["omitido"]:
    print("\nQue distingue a cada cluster:")
    print(clustering["tablas"]["distintivas"].to_string(index=False))
if not correlaciones["omitido"]:
    print("\nRelaciones mas importantes:")
    print(correlaciones["tablas"]["ranking"].to_string(index=False))

# ---- graficos: se guardan todos en un solo HTML ----
figuras = generar_figuras(df, esquema, log, {
    "outliers": outliers, "clustering": clustering, "correlaciones": correlaciones})

os.makedirs("output", exist_ok=True)
partes = []
for numero, (nombre, figura) in enumerate(figuras.items()):
    partes.append(figura.to_html(full_html=False,
                                 include_plotlyjs="cdn" if numero == 0 else False))
html = ("<html><head><meta charset='utf-8'><title>Prueba fase 2</title></head>"
        "<body style='font-family:sans-serif;max-width:1100px;margin:auto'>"
        + "<hr>".join(partes) + "</body></html>")
destino = os.path.join("output", "prueba_fase2.html")
with open(destino, "w", encoding="utf-8") as archivo:
    archivo.write(html)
print(f"\nGraficos generados: {list(figuras)}")
print(f"Archivo creado: {destino}")
webbrowser.open("file://" + os.path.abspath(destino))