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
    seccion    TEXT NOT NULL,               -- '' si falta (gasto incompleto por audio)
    categoria  TEXT NOT NULL,               -- '' si falta
    concepto   TEXT NOT NULL,               -- '' si falta
    importe    REAL NOT NULL,               -- obligatorio incluso en incompletos
    enlace     TEXT NOT NULL DEFAULT '',    -- URL de Drive (Fase 2; vacío por ahora)
    quien      TEXT NOT NULL,
    creado_en  TEXT NOT NULL,               -- marca de tiempo ISO de cuándo se registró
    estado     TEXT NOT NULL DEFAULT 'completo'  -- 'completo' | 'incompleto'
);
"""


def _migrar(con: sqlite3.Connection) -> None:
    """Migraciones idempotentes para bases de datos creadas antes de añadir columnas."""
    columnas = {fila["name"] for fila in con.execute("PRAGMA table_info(gastos)")}
    if "estado" not in columnas:
        con.execute("ALTER TABLE gastos ADD COLUMN estado TEXT NOT NULL DEFAULT 'completo'")


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
        _migrar(con)


def registro_de(factura, quien: str, enlace: str, momento: datetime,
                estado: str = "completo") -> dict:
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
        "estado": estado,
    }


def guardar_gasto(db_path, factura, quien: str, enlace: str, momento: datetime,
                  estado: str = "completo") -> int:
    """Inserta un gasto y devuelve el id que le asigna SQLite."""
    registro = registro_de(factura, quien, enlace, momento, estado)
    with closing(_conectar(db_path)) as con, con:
        cursor = con.execute(
            """
            INSERT INTO gastos
                (fecha, trimestre, seccion, categoria, concepto, importe, enlace, quien, creado_en, estado)
            VALUES
                (:fecha, :trimestre, :seccion, :categoria, :concepto, :importe, :enlace, :quien, :creado_en, :estado)
            """,
            registro,
        )
        return cursor.lastrowid


def listar_pendientes(db_path) -> list[dict]:
    """Devuelve los gastos incompletos (más recientes primero) para el comando /pendientes."""
    with closing(_conectar(db_path)) as con:
        filas = con.execute(
            """
            SELECT id, fecha, seccion, categoria, concepto, importe, quien
            FROM gastos
            WHERE estado = 'incompleto'
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(f) for f in filas]
