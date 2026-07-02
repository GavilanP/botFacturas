"""Persistencia de gastos en SQLite: la fuente de verdad local del bot.

Un solo fichero, sin servidor. Se abre una conexión nueva por operación (así es
seguro aunque el bot atienda varias cosas a la vez). El esquema se crea solo la
primera vez con init_db(); usar SQL estándar facilita migrar a PostgreSQL el día
que el proyecto lo pida.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from util import trimestre_de

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS gastos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha      TEXT NOT NULL,               -- fecha del gasto (dd/mm/aaaa)
    trimestre  TEXT NOT NULL,               -- trimestre scout calculado de la fecha
    seccion    TEXT NOT NULL,
    categoria  TEXT NOT NULL,
    concepto   TEXT NOT NULL,
    importe    REAL NOT NULL,
    enlace     TEXT NOT NULL DEFAULT '',    -- URL de Drive (Fase 2; vacío por ahora)
    quien      TEXT NOT NULL,
    creado_en  TEXT NOT NULL                -- marca de tiempo ISO de cuándo se registró
);
"""


def _conectar(db_path) -> sqlite3.Connection:
    """Abre la base de datos, creando la carpeta contenedora si no existe."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path) -> None:
    """Crea la tabla de gastos si aún no existe. Idempotente.

    `closing` garantiza cerrar la conexión; el `with con` interno confirma la
    transacción (el context manager de sqlite3 hace commit, pero NO cierra).
    """
    with closing(_conectar(db_path)) as con, con:
        con.execute(_ESQUEMA)


def registro_de(factura, quien: str, enlace: str, momento: datetime) -> dict:
    """Construye el dict de un gasto (se usa para insertar y para el log de DRY_RUN)."""
    return {
        "fecha": momento.strftime("%d/%m/%Y"),
        "trimestre": trimestre_de(momento.date()),
        "seccion": factura.seccion,
        "categoria": factura.categoria,
        "concepto": factura.concepto,
        "importe": factura.importe,
        "enlace": enlace,
        "quien": quien,
        "creado_en": momento.isoformat(timespec="seconds"),
    }


def guardar_gasto(db_path, factura, quien: str, enlace: str, momento: datetime) -> int:
    """Inserta un gasto y devuelve el id que le asigna SQLite."""
    registro = registro_de(factura, quien, enlace, momento)
    with closing(_conectar(db_path)) as con, con:
        cursor = con.execute(
            """
            INSERT INTO gastos
                (fecha, trimestre, seccion, categoria, concepto, importe, enlace, quien, creado_en)
            VALUES
                (:fecha, :trimestre, :seccion, :categoria, :concepto, :importe, :enlace, :quien, :creado_en)
            """,
            registro,
        )
        return cursor.lastrowid
