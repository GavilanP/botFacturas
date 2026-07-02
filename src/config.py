"""Carga de configuración: .env, catálogos y lista blanca de autorizados."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

from catalogos import Catalogos

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"

load_dotenv(BASE_DIR / ".env")


@dataclass
class Config:
    telegram_token: str
    sheets_id: str
    sheets_range: str
    auth_mode: str
    credentials_path: Path
    drive_raiz_id: str
    db_path: Path
    dry_run: bool
    facturas_activas: bool
    catalogos: Catalogos
    autorizados: dict[int, str]  # chat_id -> nombre

    def nombre_de(self, chat_id: int) -> str | None:
        return self.autorizados.get(chat_id)

    def esta_autorizado(self, chat_id: int) -> bool:
        return chat_id in self.autorizados


def _ruta_real_o_example(nombre_real: str, nombre_example: str) -> Path:
    """Usa el fichero real si existe; si no, cae al *.example (útil para arrancar/probar)."""
    real = CONFIG_DIR / nombre_real
    return real if real.exists() else CONFIG_DIR / nombre_example


def _cargar_autorizados(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return {int(a["chat_id"]): a["nombre"] for a in doc.get("autorizados", [])}


def _a_bool(valor: str) -> bool:
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí")


def cargar_config() -> Config:
    cred_raw = os.getenv("GOOGLE_CREDENTIALS_PATH", "config/credenciales-cuenta-servicio.json").strip()
    cred_path = Path(cred_raw)
    if not cred_path.is_absolute():
        cred_path = BASE_DIR / cred_path

    db_raw = os.getenv("DB_PATH", "data/gastos.db").strip()
    db_path = Path(db_raw)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    secciones_path = _ruta_real_o_example("secciones.yaml", "secciones.example.yaml")
    categorias_path = CONFIG_DIR / "categorias.yaml"
    autorizados_path = _ruta_real_o_example("autorizados.yaml", "autorizados.example.yaml")

    return Config(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        sheets_id=os.getenv("GOOGLE_SHEETS_ID", "").strip(),
        sheets_range=os.getenv("GOOGLE_SHEETS_RANGE", "Tabla de Gastos!A:I").strip(),
        auth_mode=os.getenv("GOOGLE_AUTH_MODE", "service_account").strip(),
        credentials_path=cred_path,
        drive_raiz_id=os.getenv("DRIVE_CARPETA_RAIZ_ID", "").strip(),
        db_path=db_path,
        dry_run=_a_bool(os.getenv("DRY_RUN", "0")),
        facturas_activas=_a_bool(os.getenv("FACTURAS_ACTIVAS", "0")),
        catalogos=Catalogos.desde_ficheros(secciones_path, categorias_path),
        autorizados=_cargar_autorizados(autorizados_path),
    )


def validar_config(cfg: Config) -> list[str]:
    """Devuelve la lista de problemas de configuración (vacía si todo está OK)."""
    problemas: list[str] = []
    if not cfg.telegram_token:
        problemas.append("Falta TELEGRAM_BOT_TOKEN en .env")
    if not cfg.autorizados:
        problemas.append("No hay usuarios autorizados (config/autorizados.yaml)")
    # Modo solo-DB: la persistencia es SQLite; no hacen falta credenciales de Google.
    # Las credenciales y carpetas de Drive solo se necesitan al subir facturas (Fase 2).
    if not cfg.dry_run and cfg.facturas_activas:
        if not cfg.credentials_path.exists():
            problemas.append(f"No se encuentra el fichero de credenciales: {cfg.credentials_path}")
        sin_carpeta = []
        for s in cfg.catalogos.codigos_secciones:
            carpeta = cfg.catalogos.carpeta_drive(s)
            if not carpeta or carpeta.startswith("PENDIENTE"):
                sin_carpeta.append(s)
        if sin_carpeta:
            problemas.append("Hay secciones sin carpeta_drive_id en secciones.yaml: " + ", ".join(sin_carpeta))
    return problemas
