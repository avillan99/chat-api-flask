"""
Fixtures de pytest para inicializar la app y cliente de pruebas.
"""

import os
import tempfile
import sys
import pytest

# Añade la carpeta raíz del repo al sys.path (para importar app)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app


@pytest.fixture
def app():
    # Crea DB temporal segura para Windows/Linux
    fd, db_path = tempfile.mkstemp(prefix="testdb_", suffix=".sqlite3")
    os.close(fd)

    # Configuración de prueba, incluida lista de palabras bloqueadas
    app = create_app({
        "TESTING": True,
        "DB_PATH": db_path,
        "BLOCKED_WORDS": ["badword"],
    })

    yield app

    # Limpieza de archivos SQLite (incluye -wal/-shm en Windows)
    for suf in ("", "-wal", "-shm"):
        try:
            os.remove(db_path + suf)
        except (FileNotFoundError, PermissionError):
            pass


@pytest.fixture
def client(app):
    """Cliente de pruebas Flask vinculado a la app de test."""
    return app.test_client()
