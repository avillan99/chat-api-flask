"""
Carga configuración desde config.json y expone constantes globales (DB_PATH, PROFANITY_LIST).
"""

import json, os

def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config(filename="config.json"):
    # Abre y parsea el archivo de configuración principal del proyecto
    with open(os.path.join(_root(), filename), encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

DB_PATH = CONFIG.get("db_path", "database.sqlite")
PROFANITY_LIST = CONFIG.get("blocked_words", [])
