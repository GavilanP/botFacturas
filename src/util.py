"""Utilidades pequeñas y sin dependencias externas (fáciles de testear)."""
from __future__ import annotations

import unicodedata
from datetime import date


def normalizar(texto: str | None) -> str:
    """Normaliza para comparar: sin acentos, en minúsculas y sin espacios sobrantes."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sin_acentos.lower().split())


def trimestre_de(fecha: date) -> str:
    """Trimestre de la ronda scout a partir de la fecha (criterio por defecto, ajustable).

    - Sep, Oct, Nov, Dic       -> "1º"
    - Ene, Feb, Mar            -> "2º"
    - Abr, May, Jun, Jul, Ago  -> "3º"
    """
    mes = fecha.month
    if mes >= 9:
        return "1º"
    if mes <= 3:
        return "2º"
    return "3º"
