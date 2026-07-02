"""Catálogos de secciones y categorías (cargados desde YAML).

Se mantiene separado de la carga de secretos (config.py) para que la validación
se pueda probar sin .env ni credenciales de Google.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from util import normalizar


@dataclass
class Catalogos:
    # codigo canónico de sección -> id de carpeta de Drive
    secciones_drive: dict[str, str]
    # codigo de sección -> nombre de la lista de categorías que usa
    seccion_a_lista: dict[str, str]
    # nombre de lista -> lista de codigos canónicos de categoría
    listas: dict[str, list[str]]
    # nombre de lista -> [(grupo, [categorías])] para menús de 2 niveles (partida/bloque)
    grupos: dict[str, list] = field(default_factory=dict)

    # Índices normalizados (se calculan automáticamente)
    secciones: dict[str, str] = field(init=False)
    _cat_index: dict[str, dict[str, str]] = field(init=False)

    def __post_init__(self) -> None:
        self.secciones = {normalizar(c): c for c in self.secciones_drive}
        self._cat_index = {
            lista: {normalizar(cat): cat for cat in cats}
            for lista, cats in self.listas.items()
        }

    # --- API usada por validacion.py ---
    @property
    def codigos_secciones(self) -> list[str]:
        return list(self.secciones_drive.keys())

    def categorias_de(self, codigo_seccion: str) -> dict[str, str]:
        """Devuelve {norm(categoria): codigo} para la sección dada."""
        lista = self.seccion_a_lista.get(codigo_seccion)
        return self._cat_index.get(lista, {})

    def codigos_categorias_de(self, codigo_seccion: str) -> list[str]:
        lista = self.seccion_a_lista.get(codigo_seccion)
        return list(self.listas.get(lista, []))

    def carpeta_drive(self, codigo_seccion: str) -> str | None:
        return self.secciones_drive.get(codigo_seccion)

    # --- API para los menús de botones (2 niveles) ---
    def grupos_de(self, codigo_seccion: str) -> list[str]:
        """Nombres de partida/bloque de la sección (vacío si esa sección no agrupa)."""
        lista = self.seccion_a_lista.get(codigo_seccion)
        return [g for g, _ in self.grupos.get(lista, [])]

    def categorias_de_grupo(self, codigo_seccion: str, grupo: str) -> list[str]:
        lista = self.seccion_a_lista.get(codigo_seccion)
        for g, cats in self.grupos.get(lista, []):
            if g == grupo:
                return cats
        return []

    # --- Carga desde ficheros ---
    @classmethod
    def desde_ficheros(cls, secciones_path: Path, categorias_path: Path) -> "Catalogos":
        with open(secciones_path, encoding="utf-8") as f:
            sec_doc = yaml.safe_load(f) or {}
        with open(categorias_path, encoding="utf-8") as f:
            cat_doc = yaml.safe_load(f) or {}

        secciones_drive = {
            s["codigo"]: s.get("carpeta_drive_id", "")
            for s in sec_doc.get("secciones", [])
        }

        listas: dict[str, list[str]] = {}
        grupos: dict[str, list] = {}
        for nombre, items in (cat_doc.get("listas") or {}).items():
            codigos: list[str] = []
            grupos_lista: list = []   # [(grupo, [codigos])]
            idx: dict[str, int] = {}
            for item in items:
                codigo = item["codigo"]
                codigos.append(codigo)
                g = item.get("partida") or item.get("bloque")  # None en unidades
                if g:
                    if g not in idx:
                        idx[g] = len(grupos_lista)
                        grupos_lista.append((g, []))
                    grupos_lista[idx[g]][1].append(codigo)
            listas[nombre] = codigos
            grupos[nombre] = grupos_lista

        seccion_a_lista = dict(cat_doc.get("seccion_a_lista") or {})
        return cls(
            secciones_drive=secciones_drive,
            seccion_a_lista=seccion_a_lista,
            listas=listas,
            grupos=grupos,
        )
