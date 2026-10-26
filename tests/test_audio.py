"""Pruebas de la lógica pura del flujo de audio en bot.py (sin Telegram ni IA)."""
from bot import _resumen_parcial
from core.interpretar import Propuesta
from core.validacion import Factura


def test_resumen_parcial_omite_campos_vacios():
    # Propuesta con solo sección e importe: no debe listar categoría ni concepto.
    p = Propuesta(seccion="Castores", categoria=None, concepto=None, importe=47.30)
    texto = _resumen_parcial(p)
    assert "Sección: Castores" in texto
    assert "Importe: 47.30 €" in texto
    assert "Categoría" not in texto
    assert "Concepto" not in texto


def test_resumen_parcial_con_factura_completa():
    f = Factura(seccion="Grupo", categoria="Intendencia", concepto="comida", importe=30.0)
    texto = _resumen_parcial(f)
    assert "Sección: Grupo" in texto
    assert "Categoría: Intendencia" in texto
    assert "Concepto: comida" in texto
    assert "Importe: 30.00 €" in texto


def test_resumen_parcial_factura_con_campos_vacios():
    # Un gasto incompleto se guarda con "" en los campos que faltan: no deben aparecer.
    f = Factura(seccion="Manada", categoria="", concepto="", importe=12.5)
    texto = _resumen_parcial(f)
    assert "Sección: Manada" in texto
    assert "Importe: 12.50 €" in texto
    assert "Categoría" not in texto
    assert "Concepto" not in texto
