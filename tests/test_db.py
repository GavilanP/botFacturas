"""Pruebas de la persistencia en SQLite (offline, usa una DB temporal)."""
import sqlite3
from datetime import datetime

import db
from validacion import Factura


def test_guardar_y_recuperar(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)

    factura = Factura(seccion="Castores", categoria="Material de unidad",
                      concepto="Pinturas para el local", importe=47.30)
    momento = datetime(2026, 3, 15, 10, 30, 0)  # marzo -> trimestre "2º"

    gasto_id = db.guardar_gasto(ruta, factura, quien="Ana Pérez", enlace="", momento=momento)
    assert gasto_id == 1

    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    fila = con.execute("SELECT * FROM gastos WHERE id = ?", (gasto_id,)).fetchone()

    assert fila["seccion"] == "Castores"
    assert fila["categoria"] == "Material de unidad"
    assert fila["concepto"] == "Pinturas para el local"
    assert fila["importe"] == 47.30
    assert fila["trimestre"] == "2º"
    assert fila["fecha"] == "15/03/2026"
    assert fila["quien"] == "Ana Pérez"
    assert fila["enlace"] == ""


def test_ids_incrementales(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    f = Factura(seccion="Grupo", categoria="Intendencia", concepto="x", importe=10.0)
    id1 = db.guardar_gasto(ruta, f, "Quien", "", datetime(2026, 1, 1))
    id2 = db.guardar_gasto(ruta, f, "Quien", "", datetime(2026, 1, 2))
    assert (id1, id2) == (1, 2)


def test_init_db_es_idempotente(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    db.init_db(ruta)  # llamarla dos veces no debe fallar ni borrar datos
    f = Factura(seccion="Tropa", categoria="Excursión de unidad", concepto="Autobús", importe=200.0)
    db.guardar_gasto(ruta, f, "Luis", "", datetime(2025, 10, 5))
    con = sqlite3.connect(ruta)
    assert con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 1
