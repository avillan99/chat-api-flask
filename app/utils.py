"""
Funciones utilitarias: fechas ISO, validación de timestamp,
formato de errores y censura básica de contenido.
"""

from datetime import datetime, timezone
from flask import jsonify
from app.config import PROFANITY_LIST
from flask import current_app, has_app_context

def now_iso() -> str:
    """Devuelve la fecha/hora actual en UTC en formato ISO8601."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso_datetime(s: str) -> str:
    """Valida y normaliza un timestamp ISO8601 (requiere zona horaria)."""
    s = s.strip()
    if not s:
        raise ValueError("'timestamp' no puede estar vacío")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        raise ValueError("Formato ISO inválido para 'timestamp'")
    if dt.tzinfo is None:
        raise ValueError("'timestamp' debe incluir zona horaria (e.g. 'Z' o '+00:00')")
    return dt.replace(microsecond=0).isoformat()


def error(code: str, message: str, http_status: int, details: str | None = None):
    """Construye respuesta JSON de error estandarizada."""
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    resp = {"status": "error", "error": err}
    return jsonify(resp), http_status


def sanitize_content(text: str) -> str:
    """Censura palabras prohibidas según config Flask (o lista por defecto)."""
    if has_app_context():
        blocked = current_app.config.get("BLOCKED_WORDS", PROFANITY_LIST)
    else:
        blocked = PROFANITY_LIST
    tokens = text.split()
    return " ".join("***" if t.lower() in blocked else t for t in tokens)
