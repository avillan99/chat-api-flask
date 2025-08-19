"""
Funciones auxiliares para inicializar y conectar la base de datos SQLite.
"""

import sqlite3, os
from app.config import DB_PATH

def init_db(db_path: str):
    # Crear carpeta si no existe y asegurar tabla 'messages'
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('user','system')),
                word_count INTEGER NOT NULL,
                character_count INTEGER NOT NULL,
                processed_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

def get_conn(db_path: str):
    # Devuelve conexión con filas accesibles como diccionario (sqlite3.Row)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row 
    return conn
