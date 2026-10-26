"""Pruebas del mapeo de campos a columnas de Sheets y del trimestre (offline)."""
from datetime import date, datetime

from core.sheets import construir_fila
from core.util import trimestre_de
from core.validacion import Factura


def test_orden_y_contenido_de_fila():
    f = Factura(seccion="Castores", categoria="Material de unidad", concepto="Pinturas", importe=47.30)
    fila = construir_fila(f, quien="Ana Pérez", enlace="https://drive/x", momento=datetime(2026, 6, 4, 18, 30))
    assert fila == [
        "Castores",            # A UNIDAD
        "3º",                  # B Trimestre (junio)
        "Material de unidad",  # C Categoría
        47.30,                 # D Importe (número)
        "",                    # E Factura (vacío: lo rellena tesorería)
        "04/06/2026",          # F Fecha
        "Pinturas",            # G Comentarios
        "https://drive/x",     # H Enlace factura
        "Ana Pérez",           # I Quién
    ]


def test_importe_es_numero():
    f = Factura(seccion="Grupo", categoria="Intendencia", concepto="x", importe=10.0)
    fila = construir_fila(f, quien="Quien", enlace="", momento=datetime(2026, 1, 1))
    assert isinstance(fila[3], (int, float))


def test_trimestre():
    assert trimestre_de(date(2025, 10, 1)) == "1º"
    assert trimestre_de(date(2025, 12, 31)) == "1º"
    assert trimestre_de(date(2026, 2, 1)) == "2º"
    assert trimestre_de(date(2026, 3, 31)) == "2º"
    assert trimestre_de(date(2026, 4, 1)) == "3º"
    assert trimestre_de(date(2026, 8, 31)) == "3º"
