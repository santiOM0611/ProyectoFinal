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


# Outliers 
ZSCORE_UMBRAL = 3            
IQR_FACTOR = 1.5            
CONTAMINACION = 0.05         
MAX_OUTLIERS_TABLA = 10    

#  Clustering 
SEMILLA = 42                 
MIN_COLUMNAS_CLUSTERING = 2
MIN_FILAS_CLUSTERING = 20
K_MIN = 2
K_MAX = 8                    
MUESTRA_SILHOUETTE = 5000    
DBSCAN_MIN_MUESTRAS = 5
TOP_VARIABLES_CLUSTER = 3    

# Correlaciones
CORR_FUERTE = 0.7
CORR_MODERADA = 0.4
CORR_MULTICOLINEALIDAD = 0.9
ETA_FUERTE = 0.14           
ETA_MODERADA = 0.06
CRAMER_FUERTE = 0.5        
CRAMER_MODERADO = 0.3
P_MAXIMO = 0.05             
MIN_ESPERADO_CHI2 = 5        
MAX_PARES_TABLA = 50
MAX_RELACIONES = 15

# Graficos
MAX_HISTOGRAMAS = 12
MAX_BOXPLOTS = 8
MAX_CATEGORICAS = 6
MAX_VARIABLES_HEATMAP = 20
MAX_DISPERSIONES = 4


# Insights
ASIMETRIA_ALTA = 1.0       
DOMINANCIA_CATEGORIA = 80    
NULOS_NOTABLES = 5           
NULOS_GRAVES = 20            
MAX_HALLAZGOS = 14           

# Interfaz web 
MAX_SUBIDA_MB = 50           
PUERTO = 5000
CARPETA_SALIDA = "output"
MAX_REPORTES_EN_MEMORIA = 5  