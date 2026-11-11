import io
from pathlib import Path

from modules.dashboard import construir_dashboard
from modules.pipeline import analizar_archivo, datos_enriquecidos
from web.app import crear_app


def test_pipeline_completo(csv_mixto):
    r = analizar_archivo(csv_mixto)
    for clave in ("outliers", "clustering", "correlaciones", "figuras", "hallazgos"):
        assert clave in r
    assert not r["outliers"]["omitido"] and not r["clustering"]["omitido"]
    assert len(r["hallazgos"]) > 0
    assert {"es_outlier", "cluster_kmeans"} <= set(datos_enriquecidos(r).columns)


def test_dashboard_es_html_valido(csv_mixto):
    html = construir_dashboard(analizar_archivo(csv_mixto), embebido=False)
    assert html.startswith("<!doctype html>") and "Hallazgos principales" in html


def test_ignorar_columnas_en_clustering(csv_mixto):
    r = analizar_archivo(csv_mixto, excluir_clustering=["ruido"])
    assert r["clustering"]["resumen"]["variables_usadas"] == 2


def _subir(cliente, archivos):
    datos = {"archivo": [(io.BytesIO(c), n) for n, c in archivos]}
    return cliente.post("/analizar", data=datos, content_type="multipart/form-data")


def test_web_un_archivo_redirige_al_reporte(csv_mixto):
    cliente = crear_app().test_client()
    contenido = Path(csv_mixto).read_bytes()
    resp = _subir(cliente, [("datos.csv", contenido)])
    assert resp.status_code == 302
    assert cliente.get(resp.headers["Location"]).status_code == 200


def test_web_varios_archivos_y_uno_malo(csv_mixto):
    cliente = crear_app().test_client()
    contenido = Path(csv_mixto).read_bytes()
    resp = _subir(cliente, [("a.csv", contenido), ("b.csv", contenido), ("c.txt", b"x")])
    texto = resp.data.decode()
    assert resp.status_code == 200
    assert texto.count("ver reporte") == 2 and "No se pudo analizar" in texto


def test_web_sin_archivo_da_error_400():
    assert crear_app().test_client().post("/analizar", data={}).status_code == 400

def test_hallazgos_con_el_formato_esperado(csv_mixto):
    titulos = " | ".join(h["titulo"] for h in analizar_archivo(csv_mixto)["hallazgos"])
    assert "agrupaciones principales según" in titulos
    assert "tienen valores atípicos en" in titulos
    assert "correlación (r=" in titulos
    assert "explica un" in titulos and "de la variación en" in titulos


def test_web_rechaza_mas_archivos_del_maximo(csv_mixto):
    from modules import config
    cliente = crear_app().test_client()
    contenido = Path(csv_mixto).read_bytes()
    archivos = [(f"{i}.csv", contenido) for i in range(config.MAX_ARCHIVOS + 1)]
    assert _subir(cliente, archivos).status_code == 400