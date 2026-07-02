"""Credenciales de Google según el modo configurado (service_account | oauth).

Aísla la autenticación para que cambiar de modo sea solo configuración, sin tocar
drive.py ni sheets.py.
"""
from __future__ import annotations

from pathlib import Path

# Permisos solicitados. 'drive' (completo) evita fricciones al subir a carpetas/Unidades
# compartidas; si prefieres mínimo privilegio puedes probar 'drive.file'.
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def credenciales(auth_mode: str, credentials_path: Path):
    """Devuelve credenciales válidas para Drive y Sheets."""
    if auth_mode == "service_account":
        from google.oauth2 import service_account

        return service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=SCOPES
        )
    if auth_mode == "oauth":
        return _credenciales_oauth(credentials_path)
    raise ValueError(f"GOOGLE_AUTH_MODE desconocido: {auth_mode!r} (usa 'service_account' u 'oauth')")


def _credenciales_oauth(credentials_path: Path):
    """Flujo OAuth de escritorio; cachea el token junto al fichero de credenciales."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = credentials_path.parent / "token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds
