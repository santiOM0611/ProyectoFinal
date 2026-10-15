# Parametros globales del proyecto

# Carga de archivos
EXTENSIONES_PERMITIDAS = (".csv", ".xlsx", ".xls")
CODIFICACIONES = ("utf-8-sig", "utf-8", "latin-1")  
MIN_FILAS = 10
MIN_COLUMNAS = 2

# Limpieza
MAX_NULOS_COLUMNA = 0.40     
UMBRAL_CONVERSION = 0.90     
VALOR_DESCONOCIDO = "Desconocido"
VALORES_NULOS = ("?", "-", "--", "s/d", "S/D", "n/d", "N/D")

# Deteccion de tipos
MAX_CATEGORIAS = 30          
MAX_CATEGORIAS_GRANDE = 50   
RATIO_CATEGORIA = 0.5       
RATIO_CATEGORIA_GRANDE = 0.05
RATIO_ID = 0.95             
VALORES_BOOLEANOS = {
    "si", "sí", "no", "true", "false", "yes", "verdadero", "falso", "s", "n", "y",
}

# Estadisticas
TOP_CATEGORIAS = 5           