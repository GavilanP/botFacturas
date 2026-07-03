"""Pruebas de la parte PURA de interpretar.py (sin Ollama ni Whisper, offline)."""
from interpretar import Propuesta, casar_con_catalogos, construir_prompt, extraer_json
from util import normalizar


class _CatalogosFake:
    """Catálogo mínimo con la misma API que usa interpretar.py."""
    codigos_secciones = ["Castores", "Grupo"]
    secciones = {normalizar(s): s for s in codigos_secciones}
    _cats = {
        "Castores": ["Material de unidad", "Excursión de unidad"],
        "Grupo": ["Intendencia"],
    }

    def categorias_de(self, seccion):
        return {normalizar(c): c for c in self._cats.get(seccion, [])}

    def codigos_categorias_de(self, seccion):
        return self._cats.get(seccion, [])


CAT = _CatalogosFake()


# ---------- construir_prompt ----------

def test_prompt_incluye_el_catalogo_de_categorias():
    prompt = construir_prompt("Castores, material, pinturas, 10 euros", CAT)
    # El prompt debe listar las secciones con sus categorías válidas, para que el
    # modelo elija la canónica en vez de depender del fuzzy.
    assert "Castores: Material de unidad, Excursión de unidad" in prompt
    assert "Grupo: Intendencia" in prompt
    assert "Castores, material, pinturas, 10 euros" in prompt


# ---------- extraer_json ----------

def test_extraer_json_limpio():
    assert extraer_json('{"importe": 47.30}') == {"importe": 47.30}


def test_extraer_json_con_vallas_markdown():
    crudo = '```json\n{"seccion": "Castores"}\n```'
    assert extraer_json(crudo) == {"seccion": "Castores"}


def test_extraer_json_con_texto_alrededor():
    crudo = 'Claro, aquí tienes: {"concepto": "pinturas"} espero que sirva'
    assert extraer_json(crudo) == {"concepto": "pinturas"}


def test_extraer_json_invalido_devuelve_vacio():
    assert extraer_json("no hay json aquí") == {}
    assert extraer_json('{"roto": ') == {}


# ---------- casar_con_catalogos ----------

def test_gasto_completo():
    datos = {"seccion": "castores", "categoria": "material de unidad",
             "concepto": "Pinturas para el local", "importe": 47.30}
    p = casar_con_catalogos(datos, CAT)
    assert p.completa
    assert (p.seccion, p.categoria) == ("Castores", "Material de unidad")
    assert p.concepto == "Pinturas para el local"
    assert p.importe == 47.30


def test_seccion_con_errata_casa_por_fuzzy():
    datos = {"seccion": "los castores", "categoria": "material unidad",
             "concepto": "x", "importe": 10}
    p = casar_con_catalogos(datos, CAT)
    assert p.seccion == "Castores"
    assert p.categoria == "Material de unidad"
    assert p.avisos  # debe avisar de que casó de forma difusa


def test_faltan_campos_se_listan():
    p = casar_con_catalogos({"concepto": "algo"}, CAT)
    assert not p.completa
    assert "sección" in p.faltan
    assert "categoría" in p.faltan
    assert "importe" in p.faltan
    assert "concepto" not in p.faltan


def test_importe_en_texto_se_parsea():
    datos = {"seccion": "Grupo", "categoria": "Intendencia",
             "concepto": "x", "importe": "47,30 €"}
    p = casar_con_catalogos(datos, CAT)
    assert p.importe == 47.30


def test_importe_negativo_o_cero_no_vale():
    p = casar_con_catalogos({"seccion": "Grupo", "categoria": "Intendencia",
                             "concepto": "x", "importe": 0}, CAT)
    assert "importe" in p.faltan


def test_categoria_sin_seccion_falta():
    # Sin sección no se puede validar la categoría (depende de ella).
    p = casar_con_catalogos({"categoria": "Intendencia", "concepto": "x", "importe": 5}, CAT)
    assert "sección" in p.faltan and "categoría" in p.faltan


def test_todo_vacio():
    p = casar_con_catalogos({}, CAT)
    assert p.faltan == ["sección", "categoría", "concepto", "importe"]
