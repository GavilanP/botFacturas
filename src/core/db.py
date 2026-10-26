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

from .util import trimestre_de

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

# Presupuesto por sección (la sección es el eje): una fila por sección con su importe asignado.
# Se usa para Grupo y Campamento (importe único). Las UNIDADES no usan esto: su presupuesto
# se CALCULA a partir de los parámetros + el censo (ver más abajo).
_ESQUEMA_PRESUPUESTOS = """
CREATE TABLE IF NOT EXISTS presupuestos (
    seccion  TEXT PRIMARY KEY,      -- código canónico de la sección
    importe  REAL NOT NULL DEFAULT 0 -- cantidad presupuestada (euros)
);
"""

# Presupuesto de Grupo y Campamento: por categoría y trimestre (una fila por celda).
_ESQUEMA_PRESUPUESTO_CAT = """
CREATE TABLE IF NOT EXISTS presupuesto_categoria (
    seccion    TEXT NOT NULL,
    categoria  TEXT NOT NULL,
    trimestre  TEXT NOT NULL,      -- '1º' | '2º' | '3º'
    importe    REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (seccion, categoria, trimestre)
);
"""

# Parámetros compartidos para calcular el presupuesto de las unidades (€ por persona, mínimo).
_ESQUEMA_PARAMETROS = """
CREATE TABLE IF NOT EXISTS parametros (
    clave  TEXT PRIMARY KEY,
    valor  REAL NOT NULL DEFAULT 0
);
"""

# Censo por unidad (educandos + scouters = personas), base del cálculo del presupuesto de unidad.
_ESQUEMA_CENSO = """
CREATE TABLE IF NOT EXISTS censo (
    seccion    TEXT PRIMARY KEY,
    educandos  INTEGER NOT NULL DEFAULT 0,
    scouters   INTEGER NOT NULL DEFAULT 0
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
        con.execute(_ESQUEMA_PRESUPUESTOS)
        con.execute(_ESQUEMA_PRESUPUESTO_CAT)
        con.execute(_ESQUEMA_PARAMETROS)
        con.execute(_ESQUEMA_CENSO)
        _migrar(con)
        # La sección es el eje principal de consulta (todo se filtra por ella primero),
        # así que le damos un índice para que las agrupaciones/filtros sean rápidos.
        con.execute("CREATE INDEX IF NOT EXISTS idx_gastos_seccion ON gastos(seccion)")


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


# --- Consultas y edición para la web de tesorería (Paso 2) ---

# Todas las columnas de un gasto, en el orden en que se muestran/editan.
_COLUMNAS = "id, fecha, trimestre, seccion, categoria, concepto, importe, enlace, quien, creado_en, estado"

# Campos que la web puede modificar (no se tocan id ni creado_en).
_CAMPOS_EDITABLES = frozenset(
    {"fecha", "trimestre", "seccion", "categoria", "concepto", "importe", "enlace", "quien", "estado"}
)


def listar_gastos(db_path, *, seccion=None, trimestre=None, estado=None) -> list[dict]:
    """Lista los gastos (más recientes primero) con filtros opcionales por igualdad exacta."""
    clausulas: list[str] = []
    params: dict = {}
    for campo, valor in (("seccion", seccion), ("trimestre", trimestre), ("estado", estado)):
        if valor:
            clausulas.append(f"{campo} = :{campo}")
            params[campo] = valor
    where = ("WHERE " + " AND ".join(clausulas)) if clausulas else ""
    with closing(_conectar(db_path)) as con:
        filas = con.execute(
            f"SELECT {_COLUMNAS} FROM gastos {where} ORDER BY id DESC", params
        ).fetchall()
    return [dict(f) for f in filas]


def obtener_gasto(db_path, gasto_id: int) -> dict | None:
    """Devuelve un gasto por su id, o None si no existe."""
    with closing(_conectar(db_path)) as con:
        fila = con.execute(
            f"SELECT {_COLUMNAS} FROM gastos WHERE id = ?", (gasto_id,)
        ).fetchone()
    return dict(fila) if fila else None


def actualizar_gasto(db_path, gasto_id: int, campos: dict) -> bool:
    """Actualiza los campos editables indicados de un gasto. Devuelve True si cambió una fila."""
    cambios = {k: v for k, v in campos.items() if k in _CAMPOS_EDITABLES}
    if not cambios:
        return False
    set_sql = ", ".join(f"{k} = :{k}" for k in cambios)
    params = {**cambios, "_id": gasto_id}
    with closing(_conectar(db_path)) as con, con:
        cursor = con.execute(f"UPDATE gastos SET {set_sql} WHERE id = :_id", params)
        return cursor.rowcount > 0


def borrar_gasto(db_path, gasto_id: int) -> bool:
    """Borra un gasto por su id. Devuelve True si existía y se borró."""
    with closing(_conectar(db_path)) as con, con:
        cursor = con.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
        return cursor.rowcount > 0


def obtener_presupuestos(db_path) -> dict:
    """Devuelve {seccion: importe presupuestado} para todas las secciones con presupuesto."""
    with closing(_conectar(db_path)) as con:
        filas = con.execute("SELECT seccion, importe FROM presupuestos").fetchall()
    return {f["seccion"]: f["importe"] for f in filas}


def fijar_presupuesto(db_path, seccion: str, importe: float) -> None:
    """Asigna (o actualiza) el presupuesto de una sección. Idempotente por sección."""
    with closing(_conectar(db_path)) as con, con:
        con.execute(
            """
            INSERT INTO presupuestos (seccion, importe) VALUES (:seccion, :importe)
            ON CONFLICT(seccion) DO UPDATE SET importe = excluded.importe
            """,
            {"seccion": seccion, "importe": importe},
        )


def obtener_presupuesto_categorias(db_path, seccion: str) -> dict:
    """Presupuesto de una sección por categoría y trimestre: {(categoria, trimestre): importe}."""
    with closing(_conectar(db_path)) as con:
        filas = con.execute(
            "SELECT categoria, trimestre, importe FROM presupuesto_categoria WHERE seccion = ?",
            (seccion,),
        ).fetchall()
    return {(f["categoria"], f["trimestre"]): f["importe"] for f in filas}


def fijar_presupuesto_categoria(db_path, seccion: str, categoria: str, trimestre: str, importe: float) -> None:
    """Asigna (o actualiza) el presupuesto de una celda (sección · categoría · trimestre)."""
    with closing(_conectar(db_path)) as con, con:
        con.execute(
            """
            INSERT INTO presupuesto_categoria (seccion, categoria, trimestre, importe)
            VALUES (:s, :c, :t, :i)
            ON CONFLICT(seccion, categoria, trimestre) DO UPDATE SET importe = excluded.importe
            """,
            {"s": seccion, "c": categoria, "t": trimestre, "i": importe},
        )


def gastado_categoria_trimestre(db_path, seccion: str) -> dict:
    """Gastado de una sección agrupado por categoría y trimestre: {(categoria, trimestre): total}."""
    with closing(_conectar(db_path)) as con:
        filas = con.execute(
            "SELECT categoria, trimestre, SUM(importe) AS total "
            "FROM gastos WHERE seccion = ? GROUP BY categoria, trimestre",
            (seccion,),
        ).fetchall()
    return {(f["categoria"], f["trimestre"]): f["total"] for f in filas}


def obtener_parametros(db_path) -> dict:
    """Devuelve {clave: valor} de los parámetros de cálculo (€/persona, mínimo)."""
    with closing(_conectar(db_path)) as con:
        filas = con.execute("SELECT clave, valor FROM parametros").fetchall()
    return {f["clave"]: f["valor"] for f in filas}


def fijar_parametro(db_path, clave: str, valor: float) -> None:
    """Asigna (o actualiza) un parámetro de cálculo."""
    with closing(_conectar(db_path)) as con, con:
        con.execute(
            "INSERT INTO parametros (clave, valor) VALUES (:clave, :valor) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            {"clave": clave, "valor": valor},
        )


def obtener_censo(db_path) -> dict:
    """Devuelve {seccion: {'educandos': n, 'scouters': n}} del censo guardado."""
    with closing(_conectar(db_path)) as con:
        filas = con.execute("SELECT seccion, educandos, scouters FROM censo").fetchall()
    return {f["seccion"]: {"educandos": f["educandos"], "scouters": f["scouters"]} for f in filas}


def fijar_censo(db_path, seccion: str, educandos: int, scouters: int) -> None:
    """Asigna (o actualiza) el censo de una unidad."""
    with closing(_conectar(db_path)) as con, con:
        con.execute(
            "INSERT INTO censo (seccion, educandos, scouters) VALUES (:s, :e, :sc) "
            "ON CONFLICT(seccion) DO UPDATE SET educandos = excluded.educandos, "
            "scouters = excluded.scouters",
            {"s": seccion, "e": educandos, "sc": scouters},
        )


def resumen_seccion(db_path, seccion: str) -> dict:
    """Balance de UNA sección: total, nº de apuntes y desglose por categoría y trimestre.

    La sección es el eje del sistema, así que este es el resumen que se ve al fijar una
    sección como contexto activo en la web.
    """
    with closing(_conectar(db_path)) as con:
        total = con.execute(
            "SELECT COALESCE(SUM(importe), 0) AS total, COUNT(*) AS n FROM gastos WHERE seccion = ?",
            (seccion,),
        ).fetchone()
        por_categoria = con.execute(
            "SELECT categoria, SUM(importe) AS total, COUNT(*) AS n "
            "FROM gastos WHERE seccion = ? GROUP BY categoria ORDER BY total DESC",
            (seccion,),
        ).fetchall()
        por_trimestre = con.execute(
            "SELECT trimestre, SUM(importe) AS total, COUNT(*) AS n "
            "FROM gastos WHERE seccion = ? GROUP BY trimestre ORDER BY trimestre",
            (seccion,),
        ).fetchall()
    return {
        "total": total["total"],
        "n": total["n"],
        "por_categoria": [dict(f) for f in por_categoria],
        "por_trimestre": [dict(f) for f in por_trimestre],
    }


def resumen_balances(db_path) -> dict:
    """Agregados para el panel: total global y sumas por sección, categoría y trimestre."""
    with closing(_conectar(db_path)) as con:
        total = con.execute(
            "SELECT COALESCE(SUM(importe), 0) AS total, COUNT(*) AS n FROM gastos"
        ).fetchone()
        por_seccion = con.execute(
            "SELECT seccion, SUM(importe) AS total, COUNT(*) AS n "
            "FROM gastos GROUP BY seccion ORDER BY total DESC"
        ).fetchall()
        por_categoria = con.execute(
            "SELECT seccion, categoria, SUM(importe) AS total, COUNT(*) AS n "
            "FROM gastos GROUP BY seccion, categoria ORDER BY total DESC"
        ).fetchall()
        por_trimestre = con.execute(
            "SELECT trimestre, SUM(importe) AS total, COUNT(*) AS n "
            "FROM gastos GROUP BY trimestre ORDER BY trimestre"
        ).fetchall()
    return {
        "total": total["total"],
        "n": total["n"],
        "por_seccion": [dict(f) for f in por_seccion],
        "por_categoria": [dict(f) for f in por_categoria],
        "por_trimestre": [dict(f) for f in por_trimestre],
    }
