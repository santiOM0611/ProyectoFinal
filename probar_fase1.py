"""
Prueba rapida de los modulos de la fase 1.
Uso (desde la raiz del proyecto):
    python probar_fase1.py data/ejemplo_ventas.csv
    python probar_fase1.py "data/libro.xlsx" "NombreHoja"
"""

import sys

import pandas as pd

from modules.cleaner import limpiar
from modules.loader import ErrorDeCarga, cargar_archivo
from modules.stats import calcular_estadisticas
from modules.type_detector import detectar_tipos, resumen_tipos

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

ruta = sys.argv[1] if len(sys.argv) > 1 else "data/ejemplo_ventas.csv"
hoja = sys.argv[2] if len(sys.argv) > 2 else None

try:
    df, metadata = cargar_archivo(ruta, hoja)
except ErrorDeCarga as error:
    print(f"ERROR: {error}")
    sys.exit(1)

print("=== 1. CARGA ===")
print(metadata)

df_limpio, log = limpiar(df)
print("\n=== 2. LIMPIEZA ===")
for clave, valor in log.items():
    print(f"{clave}: {valor}")

esquema = detectar_tipos(df_limpio)
print("\n=== 3. TIPOS ===")
for columna, tipo in esquema.items():
    print(f"{columna:<20} {tipo}")
print(resumen_tipos(esquema))

estadisticas = calcular_estadisticas(df_limpio, esquema)
print("\n=== 4. ESTADISTICAS ===")
print("\nNumericas:")
print(estadisticas["numericas"])
print("\nCategoricas:")
for columna, info in estadisticas["categoricas"].items():
    print(f"\n{columna} ({info['unicos']} valores, moda = {info['moda']})")
    print(info["top"].to_string(index=False))
print("\nTemporales:")
for columna, info in estadisticas["temporales"].items():
    print(columna, info)
print("\nExcluidas del analisis:", estadisticas["excluidas"])