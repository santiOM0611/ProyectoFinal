import pandas as pd
import pytest

from modules.loader import ErrorDeCarga, cargar_archivo, cargar_varios


def test_carga_csv_con_coma(csv_mixto):
    df, meta = cargar_archivo(csv_mixto)
    assert df.shape == (200, 5)
    assert meta["filas"] == 200 and meta["extension"] == ".csv"


def test_detecta_punto_y_coma(tmp_path, df_mixto):
    ruta = tmp_path / "puntoycoma.csv"
    df_mixto.to_csv(ruta, index=False, sep=";")
    df, _ = cargar_archivo(str(ruta))
    assert df.shape[1] == 5


def test_carga_excel_y_hoja(tmp_path, df_mixto):
    ruta = tmp_path / "libro.xlsx"
    with pd.ExcelWriter(ruta) as w:
        df_mixto.to_excel(w, sheet_name="Ventas", index=False)
    df, meta = cargar_archivo(str(ruta), "Ventas")
    assert len(df) == 200 and meta["hoja"] == "Ventas"


def test_archivo_inexistente():
    with pytest.raises(ErrorDeCarga):
        cargar_archivo("no_existe.csv")


def test_extension_no_soportada(tmp_path):
    ruta = tmp_path / "datos.txt"
    ruta.write_text("a,b\n1,2\n")
    with pytest.raises(ErrorDeCarga):
        cargar_archivo(str(ruta))


def test_archivo_muy_pequeno(tmp_path):
    ruta = tmp_path / "chico.csv"
    ruta.write_text("a,b\n1,2\n3,4\n")
    with pytest.raises(ErrorDeCarga):
        cargar_archivo(str(ruta))


def test_varios_archivos_un_malo_no_detiene_a_los_demas(csv_mixto):
    resultados, errores = cargar_varios([csv_mixto, "no_existe.csv"])
    assert len(resultados) == 1 and len(errores) == 1