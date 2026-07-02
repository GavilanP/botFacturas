"""Parseo y validación del mensaje de factura (puro, sin red -> fácil de testear).

Formato esperado del caption:
    SECCIÓN | CATEGORÍA | CONCEPTO | IMPORTE
Ejemplo:
    Castores | Material de unidad | Pinturas para el local | 47,30
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from util import normalizar

N_CAMPOS = 4
# Se acepta un dato por línea (cómodo en el móvil) o todo en una línea con «|».
SEPARADORES = r"[\n|]"
EJEMPLO = "Castores\nMaterial de unidad\nCena fin de ronda\n47,30"

_FORMATO = (
    "Envíalo así, cada dato en una línea:\n"
    "Sección\nCategoría\nConcepto\nImporte\n\n"
    "Ejemplo:\n" + EJEMPLO + "\n\n"
    "(También vale en una sola línea separando con «|».)"
)


@dataclass
class Factura:
    seccion: str    # código canónico de la sección
    categoria: str  # código canónico de la categoría
    concepto: str   # texto libre (va a "Comentarios")
    importe: float  # euros (> 0)


@dataclass
class ErrorValidacion:
    mensaje: str    # texto listo para enviar al usuario


def _parsear_importe(texto: str) -> float | None:
    """Convierte '47,30', '47.30', '1.234,50' o '12,50 €' a float (>0). None si no es válido."""
    t = texto.strip().replace("€", "").replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        # Formato es-ES: punto = miles, coma = decimal
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        valor = float(t)
    except ValueError:
        return None
    return round(valor, 2) if valor > 0 else None


def parsear(caption: str | None, catalogos) -> "Factura | ErrorValidacion":
    """Valida el caption contra los catálogos. Devuelve Factura o ErrorValidacion."""
    if not caption or not caption.strip():
        return ErrorValidacion("Falta el texto.\n\n" + _FORMATO)

    partes = [p.strip() for p in re.split(SEPARADORES, caption)]
    partes = [p for p in partes if p]
    if len(partes) != N_CAMPOS:
        return ErrorValidacion(
            "No reconozco el formato (necesito 4 datos: sección, categoría, concepto e importe).\n\n" + _FORMATO
        )

    seccion_txt, categoria_txt, concepto_txt, importe_txt = partes

    # 1) Sección
    codigo_seccion = catalogos.secciones.get(normalizar(seccion_txt))
    if not codigo_seccion:
        validas = ", ".join(catalogos.codigos_secciones)
        return ErrorValidacion(f"La sección «{seccion_txt}» no es válida.\nSecciones válidas: {validas}")

    # 2) Categoría (depende de la sección)
    categorias = catalogos.categorias_de(codigo_seccion)
    codigo_categoria = categorias.get(normalizar(categoria_txt))
    if not codigo_categoria:
        validas = ", ".join(catalogos.codigos_categorias_de(codigo_seccion))
        return ErrorValidacion(
            f"La categoría «{categoria_txt}» no es válida para {codigo_seccion}.\n"
            f"Categorías de {codigo_seccion}: {validas}"
        )

    # 3) Concepto
    if not concepto_txt:
        return ErrorValidacion("Falta el concepto (una descripción breve del gasto).\n\n" + _FORMATO)

    # 4) Importe
    importe = _parsear_importe(importe_txt)
    if importe is None:
        return ErrorValidacion(f"El importe «{importe_txt}» no es válido. Pon una cantidad en euros, p. ej. 47,30")

    return Factura(
        seccion=codigo_seccion,
        categoria=codigo_categoria,
        concepto=concepto_txt,
        importe=importe,
    )
