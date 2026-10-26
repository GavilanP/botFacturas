"""Smoke test de la web de tesorería con una DB temporal (no toca la DB real)."""
from fastapi.testclient import TestClient

from core import db
from web import app as webapp


def _cliente(tmp_path, monkeypatch):
    ruta = tmp_path / "gastos.db"
    db.init_db(ruta)
    monkeypatch.setattr(webapp, "DB", ruta)  # las rutas leen webapp.DB en cada llamada
    return TestClient(webapp.app), ruta


def _seccion_y_categoria():
    seccion = webapp.cfg.catalogos.codigos_secciones[0]
    categoria = webapp.cfg.catalogos.codigos_categorias_de(seccion)[0]
    return seccion, categoria


def test_paginas_principales_responden(tmp_path, monkeypatch):
    cliente, _ = _cliente(tmp_path, monkeypatch)
    assert cliente.get("/").status_code == 200
    assert cliente.get("/gastos").status_code == 200
    assert cliente.get("/gastos/nuevo").status_code == 200


def test_ciclo_crear_editar_borrar(tmp_path, monkeypatch):
    cliente, ruta = _cliente(tmp_path, monkeypatch)
    seccion, categoria = _seccion_y_categoria()

    # Crear
    r = cliente.post("/gastos", data={
        "fecha": "2026-03-15", "seccion": seccion, "categoria": categoria,
        "concepto": "Prueba web", "importe": "12,50", "quien": "Tester",
    }, follow_redirects=False)
    assert r.status_code == 303
    gastos = db.listar_gastos(ruta)
    assert len(gastos) == 1
    gid = gastos[0]["id"]
    assert gastos[0]["concepto"] == "Prueba web"
    assert gastos[0]["importe"] == 12.5
    assert gastos[0]["fecha"] == "15/03/2026"

    # Editar
    r = cliente.post(f"/gastos/{gid}", data={
        "fecha": "2026-03-16", "seccion": seccion, "categoria": categoria,
        "concepto": "Prueba editada", "importe": "20", "quien": "Tester",
    }, follow_redirects=False)
    assert r.status_code == 303
    editado = db.obtener_gasto(ruta, gid)
    assert editado["concepto"] == "Prueba editada"
    assert editado["importe"] == 20.0

    # Borrar
    r = cliente.post(f"/gastos/{gid}/borrar", follow_redirects=False)
    assert r.status_code == 303
    assert db.obtener_gasto(ruta, gid) is None


def test_contexto_filtra_por_seccion(tmp_path, monkeypatch):
    cliente, ruta = _cliente(tmp_path, monkeypatch)
    secs = webapp.cfg.catalogos.codigos_secciones
    s1, s2 = secs[0], secs[-1]
    c1 = webapp.cfg.catalogos.codigos_categorias_de(s1)[0]
    c2 = webapp.cfg.catalogos.codigos_categorias_de(s2)[0]
    for s, c, con in [(s1, c1, "uno"), (s2, c2, "dos")]:
        cliente.post("/gastos", data={"fecha": "2026-03-15", "seccion": s, "categoria": c,
                                       "concepto": con, "importe": "10", "quien": "t"},
                     follow_redirects=False)

    # Sin contexto: se ven los dos gastos.
    assert cliente.get("/gastos").text.count('class="apunte ') == 2

    # Fijar la sección s1 -> la app queda filtrada a s1 (un solo gasto).
    r = cliente.get(f"/contexto?sec={s1}", follow_redirects=False)
    assert r.status_code == 303
    assert cliente.cookies.get("seccion") == s1
    assert cliente.get("/gastos").text.count('class="apunte ') == 1

    # Todas las páginas responden con el contexto activo.
    for p in ["/", "/estadisticas", "/incompletos"]:
        assert cliente.get(p).status_code == 200


def _unidad_y_otra():
    sa = webapp.cfg.catalogos.seccion_a_lista
    secs = webapp.cfg.catalogos.codigos_secciones
    unidad = next(s for s in secs if sa.get(s) == "unidad")
    otra = next(s for s in secs if sa.get(s) != "unidad")
    return unidad, otra


def test_presupuesto_categorias_grupo_campamento(tmp_path, monkeypatch):
    cliente, ruta = _cliente(tmp_path, monkeypatch)
    _, otra = _unidad_y_otra()  # Grupo o Campamento (no unidad)
    cats = webapp.cfg.catalogos.codigos_categorias_de(otra)

    assert cliente.get("/presupuestos").status_code == 200

    # Guardar presupuesto de la 1ª categoría en 1º y 2º trimestre (toda la tabla de una vez).
    r = cliente.post("/presupuestos/categorias",
                     data={"seccion": otra, "imp:0:1º": "100", "imp:0:2º": "50"},
                     follow_redirects=False)
    assert r.status_code == 303
    pres = db.obtener_presupuesto_categorias(ruta, otra)
    assert pres[(cats[0], "1º")] == 100.0
    assert pres[(cats[0], "2º")] == 50.0

    # Con esa sección fijada, la tabla por categoría/trimestre responde.
    cliente.get(f"/contexto?sec={otra}", follow_redirects=False)
    assert cliente.get("/presupuestos").status_code == 200


def test_presupuesto_unidad_calculado(tmp_path, monkeypatch):
    cliente, ruta = _cliente(tmp_path, monkeypatch)
    unidad, _ = _unidad_y_otra()

    cliente.post("/presupuestos/parametros",
                 data={"material": "10", "excursion": "5", "minimo": "100"}, follow_redirects=False)
    assert db.obtener_parametros(ruta) == {
        "eur_persona_material": 10.0, "eur_persona_excursion": 5.0, "minimo_material": 100.0}

    cliente.post("/presupuestos/censo",
                 data={"seccion": unidad, "educandos": "8", "scouters": "2"}, follow_redirects=False)
    assert db.obtener_censo(ruta)[unidad] == {"educandos": 8, "scouters": 2}

    # 10 personas: Material = MAX(10×10, 100) = 100; Excursión = 10×5 = 50.
    u = webapp._presupuesto_unidad(unidad, webapp._parametros(), db.obtener_censo(ruta))
    assert u["personas"] == 10
    assert u["material"]["presupuesto"] == 100.0
    assert u["excursion"]["presupuesto"] == 50.0

    cliente.get(f"/contexto?sec={unidad}", follow_redirects=False)
    assert cliente.get("/presupuestos").status_code == 200


def test_datos_invalidos_no_crean_gasto(tmp_path, monkeypatch):
    cliente, ruta = _cliente(tmp_path, monkeypatch)
    r = cliente.post("/gastos", data={
        "fecha": "2026-03-15", "seccion": "NoExiste", "categoria": "x",
        "concepto": "y", "importe": "abc", "quien": "",
    })
    assert r.status_code == 400
    assert db.listar_gastos(ruta) == []
