"""Pruebas de validar_config: el comportamiento clave del modo solo-DB (offline)."""
from pathlib import Path

from core.config import Config, validar_config


class _CatalogosFake:
    """Catálogo mínimo para no depender de los YAML reales en los tests."""
    codigos_secciones = ["Castores"]

    def carpeta_drive(self, seccion):
        return ""  # sin carpeta configurada


def _config(**cambios) -> Config:
    base = dict(
        telegram_token="token-de-prueba",
        sheets_id="",
        sheets_range="",
        auth_mode="service_account",
        credentials_path=Path("/ruta/que/no/existe.json"),
        drive_raiz_id="",
        db_path=Path("/tmp/gastos-test.db"),
        dry_run=False,
        facturas_activas=False,
        catalogos=_CatalogosFake(),
        autorizados={123: "Ana"},
    )
    base.update(cambios)
    return Config(**base)


def test_solo_db_no_exige_credenciales_de_google():
    # Sin credenciales de Google ni Sheets, en modo solo-DB, no debe haber problemas.
    assert validar_config(_config()) == []


def test_token_y_autorizados_son_obligatorios():
    problemas = validar_config(_config(telegram_token="", autorizados={}))
    assert any("TELEGRAM_BOT_TOKEN" in p for p in problemas)
    assert any("autorizados" in p for p in problemas)


def test_facturas_activas_si_exige_credenciales_y_carpetas():
    problemas = validar_config(_config(facturas_activas=True))
    assert any("credenciales" in p for p in problemas)
    assert any("carpeta_drive" in p for p in problemas)
