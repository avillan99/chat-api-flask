"""
MVP: Chat Messages API (single-file Flask + sqlite3)
Run:
  python -m venv .venv && . .venv/bin/activate
  pip install Flask
  python app.py
Test quick:
  curl -X POST http://127.0.0.1:5000/api/messages \
    -H 'Content-Type: application/json' \
    -d '{
      "message_id": "m1",
      "session_id": "s1",
      "content": "Hola mundo",
      "timestamp": "2025-08-17T20:00:00Z",
      "sender": "user"
    }'
  curl 'http://127.0.0.1:5000/api/messages/s1?limit=10&offset=0'
"""
# from __future__ import annotations
# import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request

DB_PATH = "app.db"
PROFANITY_LIST = {"foo", "bar", "badword"}  # TODO: REEMPLAZAR

app = Flask(__name__)

# ---------- DB helpers ----------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('user','system')),
                word_count INTEGER NOT NULL,
                character_count INTEGER NOT NULL,
                processed_at TEXT NOT NULL
            );
            """
        )


# ---------- Utils ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso_datetime(s: str) -> str:
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
    # err: Dict[str, Any] = {"code": code, "message": message}
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    resp = {"status": "error", "error": err}
    return jsonify(resp), http_status


def sanitize_content(text: str) -> str:
    # MVP: censura palabras exactas, case-insensitive
    tokens = text.split()
    out = []
    for t in tokens:
        if t.lower() in PROFANITY_LIST:
            out.append("***")
        else:
            out.append(t)
    return " ".join(out)


# ---------- API ----------

@app.post("/api/messages")
def post_message():
    try:
        #Leer el request y fuerza parseo (JSON). Evalúa si el payload es JSON.
        # payload: Dict[str, Any] = request.get_json(force=True)
        payload: dict[str, Any] = request.get_json(force=True)
    except Exception:
        return error("INVALID_JSON", "El cuerpo debe ser JSON válido.", 400)

    #Evalúa campos del payload
    # required = ["message_id", "session_id", "content", "sender"]
    required = ["message_id", "session_id", "content", "timestamp", "sender"]
    for f in required:
        if f not in payload:
            return error("INVALID_FORMAT", f"Falta campo requerido: {f}", 400)

    message_id = str(payload["message_id"]).strip()
    session_id = str(payload["session_id"]).strip()
    content = str(payload["content"]).strip()
    sender = str(payload["sender"]).strip()
    # timestamp = str(payload.get("timestamp") or now_iso())
    raw_ts = str(payload["timestamp"]).strip()

    #Validación de contenido
    #TODO: No duplicar código (codigo y error HTTP)
    if not message_id or not session_id or not content:
        return error("INVALID_FORMAT", "message_id, session_id y content no pueden estar vacíos.", 400)
    
    try:
        timestamp = parse_iso_datetime(raw_ts)
    except ValueError as e:
        return error("INVALID_FORMAT", "Formato de mensaje inválido", 400, str(e))

    if sender not in ("user", "system"):
        return error("INVALID_FORMAT", "sender debe ser 'user' o 'system'.", 400)

    # Censura básica
    content_clean = sanitize_content(content)   #TODO: MODELO DE LENGUAJE?

    #Datos de la entrada de texto
    metadata = {
        "word_count": len(content_clean.split()),
        "character_count": len(content_clean),
        "processed_at": now_iso(),
    }

    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    message_id, session_id, content, timestamp, sender,
                    word_count, character_count, processed_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    message_id,
                    #TODO: server_message_id: Generar id de servidor?
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

    data = {
        "message_id": message_id,
        "session_id": session_id,
        "content": content_clean,
        "timestamp": timestamp,
        "sender": sender,
        "metadata": metadata,
    }
    return jsonify({"status": "success", "data": data}), 201


@app.get("/api/messages/<session_id>")
def list_messages(session_id: str):
    # Query params simples
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
        sql += " AND sender = ?"
        params.append(sender)
    sql += " ORDER BY timestamp ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        return error("DB_ERROR", f"Error al consultar: {e}", 500)

    items = []
    for r in rows:
        items.append(
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
        )

    return jsonify({"status": "success", "data": items}), 200


# ---------- App bootstrap ----------

@app.get("/")
def health():
    return jsonify({"ok": True, "time": now_iso()})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
