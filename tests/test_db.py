"""Pruebas de la persistencia en SQLite (offline, usa una DB temporal)."""
import sqlite3
from datetime import datetime

from core import db
from core.validacion import Factura


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


def test_estado_por_defecto_es_completo(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    f = Factura(seccion="Grupo", categoria="Intendencia", concepto="x", importe=10.0)
    gid = db.guardar_gasto(ruta, f, "Quien", "", datetime(2026, 1, 1))
    con = sqlite3.connect(ruta)
    assert con.execute("SELECT estado FROM gastos WHERE id = ?", (gid,)).fetchone()[0] == "completo"


def test_guardar_gasto_incompleto(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    # Un incompleto: falta categoría y concepto (cadenas vacías); el importe sí está.
    f = Factura(seccion="Castores", categoria="", concepto="", importe=47.30)
    gid = db.guardar_gasto(ruta, f, "Ana", "", datetime(2026, 3, 15), estado="incompleto")
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    fila = con.execute("SELECT * FROM gastos WHERE id = ?", (gid,)).fetchone()
    assert fila["estado"] == "incompleto"
    assert fila["seccion"] == "Castores"
    assert fila["categoria"] == ""
    assert fila["importe"] == 47.30


def test_listar_pendientes_solo_incompletos(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    completo = Factura(seccion="Grupo", categoria="Intendencia", concepto="comida", importe=30.0)
    incompleto = Factura(seccion="Manada", categoria="", concepto="", importe=12.5)
    db.guardar_gasto(ruta, completo, "Ana", "", datetime(2026, 1, 1))
    gid_inc = db.guardar_gasto(ruta, incompleto, "Luis", "", datetime(2026, 1, 2), estado="incompleto")

    pendientes = db.listar_pendientes(ruta)
    assert len(pendientes) == 1
    assert pendientes[0]["id"] == gid_inc
    assert pendientes[0]["seccion"] == "Manada"
    assert pendientes[0]["importe"] == 12.5


def test_migracion_anade_estado_a_db_antigua(tmp_path):
    """Una DB creada antes de la columna estado se migra sin perder filas."""
    ruta = tmp_path / "gastos.db"
    # Simula el esquema antiguo (sin columna estado) con una fila ya guardada.
    con = sqlite3.connect(ruta)
    con.execute(
        """
        CREATE TABLE gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, trimestre TEXT NOT NULL,
            seccion TEXT NOT NULL, categoria TEXT NOT NULL, concepto TEXT NOT NULL,
            importe REAL NOT NULL, enlace TEXT NOT NULL DEFAULT '', quien TEXT NOT NULL,
            creado_en TEXT NOT NULL
        )
        """
    )
    con.execute(
        "INSERT INTO gastos (fecha, trimestre, seccion, categoria, concepto, importe, quien, creado_en) "
        "VALUES ('01/01/2026', '2º', 'Tropa', 'x', 'y', 5.0, 'Ana', '2026-01-01T00:00:00')"
    )
    con.commit()
    con.close()

    db.init_db(ruta)  # debe añadir la columna estado sin borrar la fila

    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    fila = con.execute("SELECT * FROM gastos WHERE id = 1").fetchone()
    assert fila["estado"] == "completo"  # las filas antiguas quedan como completas
    assert fila["seccion"] == "Tropa"
