def resultado_base(omitido=False, motivo=None):
    """Crea un resultado vacio. Si omitido=True, `motivo` explica por que."""
    return {
        "omitido": omitido,      
        "motivo": motivo,         
        "resumen": {},             
        "tablas": {},              
        "datos_graficos": {},      
        "advertencias": [],       
    }