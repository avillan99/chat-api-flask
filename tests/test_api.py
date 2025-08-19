import os
import tempfile
from app import mvp as m  # importa el módulo para tocar DB_PATH y app

def _safe_close_db():
    # Cierra cualquier conexión global que tu módulo pudiera estar usando
    for name in ("_conn", "conn", "db", "connection"):
        conn = getattr(m, name, None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            try:
                setattr(m, name, None)
            except Exception:
                pass

def _safe_unlink(path: str | None):
    if not path:
        return
    for suf in ("", "-wal", "-shm"):
        p = path + suf
        if os.path.exists(p):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            except PermissionError:
                # En Windows, si quedó un handle, esto te avisa.
                pass

def setup_module(_):
    # 0) Si quedó algo abierto de la ejecución anterior, ciérralo y limpia archivos
    old_path = getattr(m, "DB_PATH", None)
    _safe_close_db()
    if isinstance(old_path, str):
        _safe_unlink(old_path)

    # 1) Crear nueva BD temporal (mkstemp + cerrar FD = clave en Windows)
    fd, path = tempfile.mkstemp(prefix="testdb_", suffix=".sqlite3")
    os.close(fd)
    m.DB_PATH = path  # usar DB temporal
    m.init_db()
    m.app.config.update(TESTING=True)

def teardown_module(_):
    _safe_close_db()
    _safe_unlink(getattr(m, "DB_PATH", None))

def test_post_ok_guarda_y_devuelve_metadata():
    c = m.app.test_client()
    r = c.post("/api/messages", json={
        "message_id": "msg-1",
        "session_id": "s1",
        "content": "Hola mundo",
        "timestamp": "2025-08-17T20:00:00Z",
        "sender": "user",
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "success"
    data = body["data"]
    assert set(["message_id","session_id","content","timestamp","sender","metadata"]) <= set(data.keys())
    md = data["metadata"]
    assert set(["word_count","character_count","processed_at"]) <= set(md.keys())
    assert md["word_count"] == 2
    assert md["character_count"] == len("Hola mundo")

def test_post_filtra_contenido_inapropiado():
    c = m.app.test_client()
    r = c.post("/api/messages", json={
        "message_id": "msg-2",
        "session_id": "s1",
        "content": "hola badword mundo",
        "timestamp": "2025-08-17T20:00:00Z",
        "sender": "user",
    })
    assert r.status_code == 201
    content = r.get_json()["data"]["content"]
    assert content == "hola *** mundo"

def test_post_timestamp_invalido_retorma_error():
    c = m.app.test_client()
    r = c.post("/api/messages", json={
        "message_id": "msg-3",
        "session_id": "s1",
        "content": "x",
        "timestamp": "2025/08/17 20:00",  # formato inválido
        "sender": "user",
    })
    assert r.status_code == 400
    e = r.get_json()["error"]
    assert e["code"] == "INVALID_FORMAT"
    assert isinstance(e["details"], str)

def test_post_invalid_json():
    c = m.app.test_client()
    r = c.post("/api/messages", data="no json", headers={"Content-Type":"text/plain"})
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "INVALID_JSON"

def test_post_duplicate_message_id_da_409():
    c = m.app.test_client()
    payload = {
        "message_id": "dup-1",
        "session_id": "s2",
        "content": "x",
        "timestamp": "2025-08-17T20:00:00Z",
        "sender": "user",
    }
    assert c.post("/api/messages", json=payload).status_code == 201
    r = c.post("/api/messages", json=payload)
    assert r.status_code == 409
    assert r.get_json()["error"]["code"] == "DUPLICATE_MESSAGE"

def test_get_por_session_con_paginacion_y_filtro_sender():
    c = m.app.test_client()
    for i in range(3):
        c.post("/api/messages", json={
            "message_id": f"g-{i}",
            "session_id": "s3",
            "content": "hola",
            "timestamp": f"2025-08-17T20:00:0{i}Z",
            "sender": "user" if i < 2 else "system",
        })
    r = c.get("/api/messages/s3?sender=user&limit=2&offset=0")
    assert r.status_code == 200
    items = r.get_json()["data"]
    assert len(items) == 2
    assert all(x["sender"] == "user" for x in items)

def test_get_limit_offset_invalidos():
    c = m.app.test_client()
    r = c.get("/api/messages/s3?limit=abc&offset=0")
    assert r.status_code == 400
    r = c.get("/api/messages/s3?limit=0&offset=-1")
    assert r.status_code == 400
