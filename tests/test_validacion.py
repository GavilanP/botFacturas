"""Pruebas de validación del mensaje (offline, sin red ni ficheros reales)."""
from catalogos import Catalogos
from validacion import ErrorValidacion, Factura, parsear


def _catalogos() -> Catalogos:
    return Catalogos(
        secciones_drive={
            "Castores": "id1", "Manada": "id2", "Tropa": "id3", "Escultas": "id4",
            "Clan": "id5", "Grupo": "id6", "Campamento": "id7",
        },
        seccion_a_lista={
            "Castores": "unidad", "Manada": "unidad", "Tropa": "unidad",
            "Escultas": "unidad", "Clan": "unidad",
            "Grupo": "grupo", "Campamento": "campamento",
        },
        listas={
            "unidad": ["Material de unidad", "Excursión de unidad"],
            "grupo": ["Intendencia", "Formación", "Pañoletas"],
            "campamento": ["Autobuses", "Makro", "Parrillada"],
        },
    )


def test_factura_valida_unidad():
    r = parsear("Castores | Material de unidad | Pinturas | 47,30", _catalogos())
    assert isinstance(r, Factura)
    assert (r.seccion, r.categoria, r.concepto, r.importe) == (
        "Castores", "Material de unidad", "Pinturas", 47.30
    )


def test_normaliza_acentos_y_mayusculas():
    r = parsear("  castores |  material de UNIDAD | x | 1 ", _catalogos())
    assert isinstance(r, Factura)
    assert r.seccion == "Castores"
    assert r.categoria == "Material de unidad"


def test_categoria_depende_de_la_seccion():
    cat = _catalogos()
    assert isinstance(parsear("Campamento | Autobuses | Bus ida | 100", cat), Factura)
    # 'Autobuses' no es válida en una unidad
    assert isinstance(parsear("Castores | Autobuses | Bus ida | 100", cat), ErrorValidacion)


def test_seccion_invalida():
    assert isinstance(parsear("Lobatos | Material de unidad | x | 1", _catalogos()), ErrorValidacion)


def test_numero_de_campos():
    cat = _catalogos()
    assert isinstance(parsear("Castores | x | 1", cat), ErrorValidacion)          # 3 campos
    assert isinstance(parsear("Castores | a | b | c | 1", cat), ErrorValidacion)  # 5 campos


def test_importes_validos():
    cat = _catalogos()
    assert parsear("Grupo | Intendencia | x | 1.234,56", cat).importe == 1234.56
    assert parsear("Grupo | Intendencia | x | 12.50", cat).importe == 12.50
    assert parsear("Grupo | Intendencia | x | 12,50 €", cat).importe == 12.50


def test_importes_invalidos():
    cat = _catalogos()
    for malo in ("abc", "-5", "0", ""):
        assert isinstance(parsear(f"Grupo | Intendencia | x | {malo}", cat), ErrorValidacion)


def test_concepto_vacio():
    assert isinstance(parsear("Grupo | Intendencia |   | 10", _catalogos()), ErrorValidacion)


def test_caption_vacio_o_nulo():
    cat = _catalogos()
    assert isinstance(parsear(None, cat), ErrorValidacion)
    assert isinstance(parsear("   ", cat), ErrorValidacion)
