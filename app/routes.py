"""
Endpoints de la API de mensajes (crear y listar) para el servicio chat-api.
"""

import sqlite3
from typing import Any
from flask import Blueprint, current_app, request, jsonify

from .db_helpers import get_conn
from .utils import error, parse_iso_datetime, sanitize_content, now_iso

bp = Blueprint("api", __name__)


@bp.post("/messages")
def post_message():
    """Crea un nuevo mensaje en la sesión indicada."""
    try:
        payload: dict[str, Any] = request.get_json(force=True)
    except Exception:
        return error("INVALID_JSON", "El cuerpo debe ser JSON válido.", 400)

    required = ["message_id", "session_id", "content", "timestamp", "sender"]
    for f in required:
        if f not in payload:
            return error("INVALID_FORMAT", f"Falta campo requerido: {f}", 400)

    message_id = str(payload["message_id"]).strip()
    session_id = str(payload["session_id"]).strip()
    content = str(payload["content"]).strip()
    sender = str(payload["sender"]).strip()
    raw_ts = str(payload["timestamp"]).strip()

    if not message_id or not session_id or not content:
        return error("INVALID_FORMAT", "message_id, session_id y content no pueden estar vacíos.", 400)

    try:
        # Valida formato ISO y exige zona horaria explícita (Z o +offset)
        timestamp = parse_iso_datetime(raw_ts)
    except ValueError as e:
        return error("INVALID_FORMAT", "Formato de mensaje inválido", 400, str(e))

    if sender not in ("user", "system"):
        return error("INVALID_FORMAT", "sender debe ser 'user' o 'system'.", 400)

    content_clean = sanitize_content(content)

    metadata = {
        "word_count": len(content_clean.split()),
        "character_count": len(content_clean),
        "processed_at": now_iso(),
    }

    try:
        with get_conn(current_app.config["DB_PATH"]) as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    message_id, session_id, content, timestamp, sender,
                    word_count, character_count, processed_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    message_id,
                    session_id,
                    content_clean,
                    timestamp,
                    sender,
                    metadata["word_count"],
                    metadata["character_count"],
                    metadata["processed_at"],
                ),
            )
    except sqlite3.IntegrityError:
        return error("DUPLICATE_MESSAGE", "message_id ya existe.", 409)
    except Exception as e:
        return error("DB_ERROR", f"Error al guardar: {e}", 500)

    return jsonify({
        "status": "success",
        "data": {
            "message_id": message_id,
            "session_id": session_id,
            "content": content_clean,
            "timestamp": timestamp,
            "sender": sender,
            "metadata": metadata,
        },
    }), 201


@bp.get("/messages/<session_id>")
def list_messages(session_id: str):
    """Lista mensajes de una sesión, con soporte de filtros y paginación."""
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return error("INVALID_FORMAT", "limit y offset deben ser enteros.", 400)

    if limit < 1 or limit > 100 or offset < 0:
        return error("INVALID_FORMAT", "limit 1..100 y offset >= 0.", 400)

    sender = request.args.get("sender")
    if sender and sender not in ("user", "system"):
        return error("INVALID_FORMAT", "sender debe ser 'user' o 'system'.", 400)

    sql = "SELECT * FROM messages WHERE session_id = ?"
    params: list[Any] = [session_id]
    if sender:
        # Se agrega filtro dinámico solo si el query param sender está presente
        sql += " AND sender = ?"
        params.append(sender)
    sql += " ORDER BY timestamp ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        with get_conn(current_app.config["DB_PATH"]) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        return error("DB_ERROR", f"Error al consultar: {e}", 500)

    items = [
        {
            "message_id": r["message_id"],
            "session_id": r["session_id"],
            "content": r["content"],
            "timestamp": r["timestamp"],
            "sender": r["sender"],
            "metadata": {
                "word_count": r["word_count"],
                "character_count": r["character_count"],
                "processed_at": r["processed_at"],
            },
        }
        for r in rows
    ]

    return jsonify({"status": "success", "data": items}), 200
