# Punto de entrada del sistema.

import argparse
import os
import threading
import webbrowser

from modules import config
from modules.dashboard import guardar_dashboard
from modules.loader import ErrorDeCarga
from modules.pipeline import analizar_archivo
from web.app import crear_app

def analizar_desde_terminal(args):
    ignorar = [c.strip() for c in args.ignorar.split(",") if c.strip()]
    try:
        print(f"Analizando {args.archivo} ...")
        resultado = analizar_archivo(args.archivo, args.hoja, excluir_clustering=ignorar)
    except ErrorDeCarga as error:
        print(f"ERROR: {error}")
        return

    base = os.path.splitext(os.path.basename(args.archivo))[0]
    destino = os.path.join(config.CARPETA_SALIDA, f"reporte_{base}.html")
    guardar_dashboard(resultado, destino, embebido=True)

    print("\nHallazgos principales:")
    for hallazgo in resultado["hallazgos"][:6]:
        print(f"  - {hallazgo['titulo']}")
    print(f"\nReporte creado: {destino}")
    if not args.sin_abrir:
        webbrowser.open("file://" + os.path.abspath(destino))

def iniciar_servidor(args):
    app = crear_app()
    direccion = f"http://127.0.0.1:{args.puerto}"
    print(f"Servidor listo en {direccion}  (Ctrl+C para detenerlo)")
    if not args.sin_abrir:
        threading.Timer(1.0, webbrowser.open, args=[direccion]).start()
    app.run(host="127.0.0.1", port=args.puerto, debug=False)

def main():
    parser = argparse.ArgumentParser(description="Sistema de analisis exploratorio automatizado")
    parser.add_argument("archivo", nargs="?", help="CSV o Excel a analizar (si se omite, abre la web)")
    parser.add_argument("--hoja", help="hoja del Excel (por defecto, la primera)")
    parser.add_argument("--ignorar", default="",
                        help="columnas a ignorar en el clustering, separadas por coma")
    parser.add_argument("--puerto", type=int, default=config.PUERTO)
    parser.add_argument("--sin-abrir", action="store_true", help="no abrir el navegador")
    args = parser.parse_args()

    if args.archivo:
        analizar_desde_terminal(args)
    else:
        iniciar_servidor(args)

if __name__ == "__main__":
    main()