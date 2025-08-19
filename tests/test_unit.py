"""
Tests unitarios de funciones utilitarias (parse_iso_datetime, sanitize_content).
"""

import pytest
from app.utils import parse_iso_datetime, sanitize_content


def test_parse_iso_datetime_valido_con_Z():
    """Acepta formato con 'Z' y lo convierte a +00:00."""
    assert parse_iso_datetime("2025-08-17T20:00:00Z").endswith("+00:00")


def test_parse_iso_datetime_valido_con_offset():
    """Acepta formato con offset explícito (-05:00)."""
    out = parse_iso_datetime("2025-08-17T15:00:00-05:00")
    assert out.endswith("-05:00")


def test_parse_iso_datetime_sin_zona_error():
    """Falla si falta zona horaria en el timestamp."""
    with pytest.raises(ValueError) as e:
        parse_iso_datetime("2025-08-17T20:00:00")
    assert "zona horaria" in str(e.value)


def test_parse_iso_datetime_formato_invalido():
    """Falla con un formato no-ISO válido."""
    with pytest.raises(ValueError):
        parse_iso_datetime("17/08/2025 20:00")


def test_sanitize_content_censura_palabras():
    """Reemplaza palabras bloqueadas por ***."""
    original = "hola badword mundo"
    out = sanitize_content(original)
    assert out.split() == ["hola", "***", "mundo"]
