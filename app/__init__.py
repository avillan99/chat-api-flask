from flask import Flask, jsonify
from .config import DB_PATH, PROFANITY_LIST
from .db_helpers import init_db
from .routes import bp as api_bp
from .utils import now_iso

"""
Inicializa la app Flask con configuración base, crea/valida la BD SQLite,
registra el blueprint de la API y expone un endpoint raíz de salud (/).
"""

def create_app(test_config: dict | None = None):
    app = Flask(__name__)
    app.config.update(
        DB_PATH=DB_PATH,
        BLOCKED_WORDS=PROFANITY_LIST,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    init_db(app.config["DB_PATH"])

    # Registrar la API principal bajo el prefijo /api
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/")
    def root_health():
        return jsonify({"ok": True, "time": now_iso(), "service": "chat-api"})
    
    return app
