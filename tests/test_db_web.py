"""Pruebas de las consultas y edición que usa la web de tesorería (offline, DB temporal)."""
from datetime import datetime

from core import db
from core.validacion import Factura


def _sembrar(ruta):
    """Crea una DB con tres gastos conocidos y devuelve sus ids (g1, g2, incompleto)."""
    db.init_db(ruta)
    g1 = db.guardar_gasto(
        ruta, Factura("Castores", "Material de unidad", "Pinturas", 47.30),
        "Ana", "", datetime(2026, 3, 15),  # marzo -> "2º"
    )
    g2 = db.guardar_gasto(
        ruta, Factura("Manada", "Intendencia", "Comida", 30.0),
        "Luis", "", datetime(2025, 10, 5),  # octubre -> "1º"
    )
    inc = db.guardar_gasto(
        ruta, Factura("Castores", "", "", 12.5),
        "Ana", "", datetime(2026, 3, 20), estado="incompleto",
    )
    return g1, g2, inc


def test_listar_gastos_sin_filtros_ordena_por_id_desc(tmp_path):
    ruta = tmp_path / "gastos.db"
    g1, g2, inc = _sembrar(ruta)
    filas = db.listar_gastos(ruta)
    assert [f["id"] for f in filas] == [inc, g2, g1]


def test_listar_gastos_filtra_por_seccion_y_estado(tmp_path):
    ruta = tmp_path / "gastos.db"
    g1, g2, inc = _sembrar(ruta)

    castores = db.listar_gastos(ruta, seccion="Castores")
    assert {f["id"] for f in castores} == {g1, inc}

    incompletos = db.listar_gastos(ruta, estado="incompleto")
    assert [f["id"] for f in incompletos] == [inc]

    combinado = db.listar_gastos(ruta, seccion="Castores", estado="completo")
    assert [f["id"] for f in combinado] == [g1]


def test_obtener_gasto(tmp_path):
    ruta = tmp_path / "gastos.db"
    g1, _, _ = _sembrar(ruta)
    gasto = db.obtener_gasto(ruta, g1)
    assert gasto is not None
    assert gasto["concepto"] == "Pinturas"
    assert db.obtener_gasto(ruta, 9999) is None


def test_actualizar_gasto_cambia_campos_editables(tmp_path):
    ruta = tmp_path / "gastos.db"
    g1, _, _ = _sembrar(ruta)
    assert db.actualizar_gasto(ruta, g1, {"concepto": "Pinturas y brochas", "importe": 50.0}) is True
    gasto = db.obtener_gasto(ruta, g1)
    assert gasto["concepto"] == "Pinturas y brochas"
    assert gasto["importe"] == 50.0


def test_actualizar_gasto_ignora_campos_no_editables(tmp_path):
    ruta = tmp_path / "gastos.db"
    g1, _, _ = _sembrar(ruta)
    # id y creado_en no son editables: si solo se pasan esos, no hay cambios.
    assert db.actualizar_gasto(ruta, g1, {"id": 123, "creado_en": "x"}) is False
    assert db.obtener_gasto(ruta, g1)["id"] == g1


def test_actualizar_completa_un_incompleto(tmp_path):
    ruta = tmp_path / "gastos.db"
    _, _, inc = _sembrar(ruta)
    db.actualizar_gasto(ruta, inc, {"categoria": "Material de unidad", "concepto": "Cuerdas", "estado": "completo"})
    gasto = db.obtener_gasto(ruta, inc)
    assert gasto["estado"] == "completo"
    assert gasto["categoria"] == "Material de unidad"


def test_borrar_gasto(tmp_path):
    ruta = tmp_path / "gastos.db"
    g1, _, _ = _sembrar(ruta)
    assert db.borrar_gasto(ruta, g1) is True
    assert db.obtener_gasto(ruta, g1) is None
    assert db.borrar_gasto(ruta, g1) is False  # ya no existe


def test_presupuesto_categoria_upsert_y_obtener(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    db.fijar_presupuesto_categoria(ruta, "Grupo", "Formación", "1º", 200.0)
    db.fijar_presupuesto_categoria(ruta, "Grupo", "Formación", "1º", 250.0)  # misma celda -> actualiza
    db.fijar_presupuesto_categoria(ruta, "Grupo", "Formación", "2º", 90.0)
    p = db.obtener_presupuesto_categorias(ruta, "Grupo")
    assert p[("Formación", "1º")] == 250.0
    assert p[("Formación", "2º")] == 90.0


def test_gastado_categoria_trimestre(tmp_path):
    ruta = tmp_path / "gastos.db"
    _sembrar(ruta)  # Castores: Material 47,30 (marzo=2º) + incompleto '' 12,50 (marzo=2º)
    g = db.gastado_categoria_trimestre(ruta, "Castores")
    assert g[("Material de unidad", "2º")] == 47.30
    assert g[("", "2º")] == 12.5


def test_resumen_seccion(tmp_path):
    ruta = tmp_path / "gastos.db"
    _sembrar(ruta)  # Castores: g1 (47,30) + inc (12,50); Manada: g2 (30)
    cast = db.resumen_seccion(ruta, "Castores")
    assert cast["n"] == 2
    assert round(cast["total"], 2) == round(47.30 + 12.5, 2)
    cats = {f["categoria"] for f in cast["por_categoria"]}
    assert "Material de unidad" in cats

    vacia = db.resumen_seccion(ruta, "Tropa")  # sección sin gastos
    assert vacia["n"] == 0
    assert vacia["total"] == 0
    assert vacia["por_categoria"] == []


def test_presupuestos_fijar_y_obtener(tmp_path):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    assert db.obtener_presupuestos(ruta) == {}

    db.fijar_presupuesto(ruta, "Castores", 300.0)
    db.fijar_presupuesto(ruta, "Manada", 150.0)
    assert db.obtener_presupuestos(ruta) == {"Castores": 300.0, "Manada": 150.0}

    # Volver a fijar la misma sección la actualiza (no duplica).
    db.fijar_presupuesto(ruta, "Castores", 500.0)
    pres = db.obtener_presupuestos(ruta)
    assert pres["Castores"] == 500.0
    assert len(pres) == 2


def test_resumen_balances(tmp_path):
    ruta = tmp_path / "gastos.db"
    _sembrar(ruta)
    r = db.resumen_balances(ruta)
    assert r["n"] == 3
    assert round(r["total"], 2) == round(47.30 + 30.0 + 12.5, 2)

    por_seccion = {f["seccion"]: f for f in r["por_seccion"]}
    assert round(por_seccion["Castores"]["total"], 2) == round(47.30 + 12.5, 2)
    assert por_seccion["Castores"]["n"] == 2
    assert round(por_seccion["Manada"]["total"], 2) == 30.0

    trimestres = {f["trimestre"] for f in r["por_trimestre"]}
    assert trimestres == {"1º", "2º"}
