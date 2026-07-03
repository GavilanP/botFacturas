"""Interpretación del texto transcrito: sacar los campos del gasto con un LLM local.

Diseño en dos mitades para poder testear sin IA:
- _pedir_al_modelo(): habla con Ollama (qwen2.5:7b). Necesita el servidor corriendo
  y el disco de modelos montado; NO se testea offline.
- extraer_json() y casar_con_catalogos(): funciones puras que validan y mapean lo
  que devuelve el modelo contra los catálogos reales. Estas SÍ se testean.

La IA solo PROPONE: aquí no se guarda nada. El bot muestra la propuesta con los
botones ✅/❌ y solo al confirmar se escribe en la base de datos.

La `Propuesta` lleva `faltan` (campos que el modelo no encontró): hoy sirve para
pedirlos en el chat; mañana alimentará el guardado de gastos incompletos
(ver DECISIONES.md).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from util import normalizar
from validacion import parsear_importe

MODELO_POR_DEFECTO = "qwen2.5:7b"
HOST_POR_DEFECTO = "http://localhost:11434"

# Por debajo de esta puntuación (0-100) no damos por buena una coincidencia difusa.
UMBRAL_FUZZY = 80


@dataclass
class Propuesta:
    """Campos del gasto tal y como los propone la IA (pendientes de confirmar)."""
    seccion: str | None = None    # código canónico, ya casado con el catálogo
    categoria: str | None = None  # ídem
    concepto: str | None = None
    importe: float | None = None
    faltan: list[str] = field(default_factory=list)   # campos sin dato
    avisos: list[str] = field(default_factory=list)   # p. ej. "sección 'castors' → Castores"

    @property
    def completa(self) -> bool:
        return not self.faltan


def construir_prompt(texto: str, catalogos) -> str:
    secciones = ", ".join(catalogos.codigos_secciones)
    return (
        "Eres un extractor de datos para un registro de gastos de un grupo scout.\n"
        "Del siguiente texto dictado por voz, extrae estos campos y responde SOLO con un JSON:\n"
        '{"seccion": ..., "categoria": ..., "concepto": ..., "importe": ...}\n\n'
        f"- seccion: una de [{secciones}] si se menciona; si no, null.\n"
        "- categoria: la categoría del gasto tal como se diga; si no se menciona, null.\n"
        "- concepto: descripción breve del gasto; si no se puede deducir, null.\n"
        "- importe: cantidad en euros como número (usa punto decimal); si no se dice, null.\n"
        "  Ojo: el importe puede venir en palabras ('cuarenta y siete con treinta' = 47.30).\n"
        "No inventes datos que no estén en el texto.\n\n"
        f"Texto: {texto}"
    )


def extraer_json(respuesta: str) -> dict:
    """Saca el objeto JSON de la respuesta del modelo (tolera ```json ... ``` y texto extra)."""
    limpio = respuesta.strip()
    limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", limpio, flags=re.MULTILINE).strip()
    inicio, fin = limpio.find("{"), limpio.rfind("}")
    if inicio == -1 or fin == -1:
        return {}
    try:
        datos = json.loads(limpio[inicio:fin + 1])
    except json.JSONDecodeError:
        return {}
    return datos if isinstance(datos, dict) else {}


def _casar(texto: str | None, indice: dict[str, str]) -> tuple[str | None, bool]:
    """Casa un texto contra {norm(nombre): código}. Devuelve (código, fue_difuso)."""
    if not texto:
        return None, False
    exacto = indice.get(normalizar(texto))
    if exacto:
        return exacto, False
    from rapidfuzz import fuzz, process  # import perezoso

    encontrado = process.extractOne(
        normalizar(texto), list(indice.keys()), scorer=fuzz.WRatio, score_cutoff=UMBRAL_FUZZY
    )
    if encontrado:
        return indice[encontrado[0]], True
    return None, False


def casar_con_catalogos(datos: dict, catalogos) -> Propuesta:
    """Valida y mapea el JSON del modelo contra los catálogos reales (función pura)."""
    p = Propuesta()

    # Sección
    seccion_txt = datos.get("seccion")
    p.seccion, difuso = _casar(seccion_txt, catalogos.secciones)
    if p.seccion and difuso:
        p.avisos.append(f"sección «{seccion_txt}» → {p.seccion}")
    if p.seccion is None:
        p.faltan.append("sección")

    # Categoría (depende de la sección)
    categoria_txt = datos.get("categoria")
    if p.seccion:
        p.categoria, difuso = _casar(categoria_txt, catalogos.categorias_de(p.seccion))
        if p.categoria and difuso:
            p.avisos.append(f"categoría «{categoria_txt}» → {p.categoria}")
    if p.categoria is None:
        p.faltan.append("categoría")

    # Concepto
    concepto = datos.get("concepto")
    p.concepto = str(concepto).strip() if concepto else None
    if not p.concepto:
        p.faltan.append("concepto")

    # Importe (el modelo puede devolver número o texto)
    importe = datos.get("importe")
    if isinstance(importe, (int, float)) and importe > 0:
        p.importe = round(float(importe), 2)
    elif isinstance(importe, str):
        p.importe = parsear_importe(importe)
    if p.importe is None:
        p.faltan.append("importe")

    return p


def _pedir_al_modelo(prompt: str, modelo: str, host: str) -> str:
    """Llamada a Ollama. Requiere el servidor corriendo (y el disco de modelos montado)."""
    import ollama  # import perezoso

    cliente = ollama.Client(host=host)
    respuesta = cliente.chat(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        format="json",                 # fuerza JSON válido en la salida
        options={"temperature": 0},    # extracción determinista, no creativa
    )
    return respuesta["message"]["content"]


def interpretar(texto: str, catalogos, modelo: str = MODELO_POR_DEFECTO,
                host: str = HOST_POR_DEFECTO) -> Propuesta:
    """Pipeline completo: texto dictado → Propuesta casada con los catálogos."""
    crudo = _pedir_al_modelo(construir_prompt(texto, catalogos), modelo, host)
    return casar_con_catalogos(extraer_json(crudo), catalogos)
