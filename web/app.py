import os
import tempfile
import traceback
import uuid
from collections import OrderedDict

from flask import Flask, Response, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from modules import config
from modules.dashboard import construir_dashboard
from modules.loader import ErrorDeCarga
from modules.pipeline import analizar_archivo, datos_enriquecidos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def crear_app():
    app = Flask(__name__, template_folder=os.path.join(RAIZ, "templates"))
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_SUBIDA_MB * 1024 * 1024

    reportes = OrderedDict()

    def pagina_inicio(error=None, codigo=200):
        pagina = render_template("index.html", error=error, max_mb=config.MAX_SUBIDA_MB,
                                 extensiones=", ".join(config.EXTENSIONES_PERMITIDAS))
        return pagina, codigo


    # pagina principal 
    @app.get("/")
    def inicio():
        return pagina_inicio()

    #analizar un solo archivo; devuelve (identificador, error, codigo_http)
    def procesar_archivo(archivo, hoja, ignorar):
        extension = os.path.splitext(archivo.filename)[1].lower()
        if extension not in config.EXTENSIONES_PERMITIDAS:
            return None, (f"Formato no soportado ({extension or 'sin extension'}). "
                          f"Usa: {', '.join(config.EXTENSIONES_PERMITIDAS)}"), 400

        nombre_seguro = secure_filename(archivo.filename) or ("subida" + extension)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, nombre_seguro)
            archivo.save(ruta)
            try:
                resultado = analizar_archivo(ruta, hoja, excluir_clustering=ignorar)
            except ErrorDeCarga as error:
                return None, str(error), 400
            except Exception:
                traceback.print_exc()
                return None, ("Ocurrió un error inesperado al analizar el archivo. "
                              "Revisa que los datos sean una tabla válida."), 500

        resultado["metadata"]["nombre"] = archivo.filename  # nombre original, con acentos
        identificador = uuid.uuid4().hex[:10]
        reportes[identificador] = resultado
        while len(reportes) > config.MAX_REPORTES_EN_MEMORIA:
            reportes.popitem(last=False)  # se olvida el mas antiguo
        return identificador, None, 200

    #recibir uno o varios archivos y analizarlos

    @app.post("/analizar")
    def analizar():
        archivos = [a for a in request.files.getlist("archivo") if a.filename]
        if not archivos:
            return pagina_inicio("Selecciona un archivo antes de analizar.", 400)
        if len(archivos) > config.MAX_ARCHIVOS:
            return pagina_inicio(
                f"Puedes subir hasta {config.MAX_ARCHIVOS} archivos a la vez.", 400)

        hoja = request.form.get("hoja", "").strip() or None
        ignorar = [c.strip() for c in request.form.get("ignorar", "").split(",") if c.strip()]

        resultados = []  # (nombre, identificador, error)
        codigo_error = 400
        for archivo in archivos:
            identificador, error, codigo = procesar_archivo(archivo, hoja, ignorar)
            resultados.append((archivo.filename, identificador, error))
            if error:
                codigo_error = codigo

        # un solo archivo: va directo al reporte (o muestra su error)
        if len(archivos) == 1:
            _, identificador, error = resultados[0]
            if error:
                return pagina_inicio(error, codigo_error)
            return redirect(url_for("ver_reporte", identificador=identificador))

        # varios archivos: lista con un enlace por reporte
        return render_template("lote.html", resultados=resultados)

    #mostrar el reporte 
    def buscar(identificador):
        return reportes.get(identificador)

    @app.get("/reporte/<identificador>")
    def ver_reporte(identificador):
        resultado = buscar(identificador)
        if resultado is None:
            return pagina_inicio("Ese reporte ya no está disponible. Sube el archivo de nuevo.", 404)
        enlaces = {
            "descargar": url_for("descargar_reporte", identificador=identificador),
            "datos": url_for("descargar_datos", identificador=identificador),
            "nuevo": url_for("inicio"),
        }
        return construir_dashboard(resultado, embebido=False, enlaces=enlaces)

    @app.get("/reporte/<identificador>/descargar")
    def descargar_reporte(identificador):
        resultado = buscar(identificador)
        if resultado is None:
            return pagina_inicio("Ese reporte ya no está disponible. Sube el archivo de nuevo.", 404)
        base = os.path.splitext(resultado["metadata"]["nombre"])[0]
        nombre = secure_filename(f"reporte_{base}.html") or "reporte.html"
        html = construir_dashboard(resultado, embebido=True)
        return Response(html, mimetype="text/html",
                        headers={"Content-Disposition": f"attachment; filename={nombre}"})

    @app.get("/reporte/<identificador>/datos.csv")
    def descargar_datos(identificador):
        resultado = buscar(identificador)
        if resultado is None:
            return pagina_inicio("Ese reporte ya no está disponible. Sube el archivo de nuevo.", 404)
        csv = datos_enriquecidos(resultado).to_csv(index=False, encoding="utf-8-sig")
        return Response(csv, mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=datos_analizados.csv"})

    #archivo demasiado grande -
    @app.errorhandler(RequestEntityTooLarge)
    def demasiado_grande(_error):
        return pagina_inicio(f"El archivo supera el límite de {config.MAX_SUBIDA_MB} MB.", 413)

    return app