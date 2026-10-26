"""Subida de facturas a Google Drive."""
from __future__ import annotations

import io


def construir_servicio(creds):
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def subir_factura(service, carpeta_id: str, nombre: str, contenido: bytes, mimetype: str) -> str:
    """Sube el archivo (desde memoria, sin escribirlo a disco) y devuelve su webViewLink."""
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=mimetype, resumable=False)
    metadatos = {"name": nombre, "parents": [carpeta_id]}
    archivo = (
        service.files()
        .create(
            body=metadatos,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,  # necesario para Unidades compartidas
        )
        .execute()
    )
    return archivo.get("webViewLink", "")
