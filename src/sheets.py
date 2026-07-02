"""Construcción e inserción de filas en Google Sheets.

Orden de columnas de la hoja destino (alineado a "Tabla de Gastos" + 2 columnas nuevas):
  A: UNIDAD | B: Trimestre | C: Categoría | D: Importe | E: Factura |
  F: Fecha | G: Comentarios | H: Enlace factura | I: Quién

  - E "Factura" (tipo de justificante) lo deja en blanco el bot; lo rellena tesorería si quiere.
  - H "Enlace factura" es la URL del archivo en Drive.
"""
from __future__ import annotations

from datetime import datetime

from util import trimestre_de


def construir_fila(factura, quien: str, enlace: str, momento: datetime) -> list:
    """Construye la fila en el orden exacto de las columnas de la hoja."""
    return [
        factura.seccion,                # A UNIDAD
        trimestre_de(momento.date()),   # B Trimestre
        factura.categoria,              # C Categoría
        factura.importe,                # D Importe (número)
        "",                             # E Factura (tipo de justificante; lo rellena tesorería)
        momento.strftime("%d/%m/%Y"),   # F Fecha
        factura.concepto,               # G Comentarios
        enlace,                         # H Enlace factura (URL de Drive)
        quien,                          # I Quién
    ]


def construir_servicio(creds):
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def append_fila(service, spreadsheet_id: str, rango: str, fila: list) -> None:
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=rango,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [fila]},
    ).execute()
