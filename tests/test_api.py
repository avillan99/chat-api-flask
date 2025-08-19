"""
Tests de integración para la API de mensajes (/api/messages).
"""

def test_post_ok_guarda_y_devuelve_metadata(client):
    """POST válido guarda el mensaje y devuelve metadata correcta."""
    r = client.post("/api/messages", json={
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
    assert {"message_id","session_id","content","timestamp","sender","metadata"} <= set(data.keys())
    md = data["metadata"]
    assert {"word_count","character_count","processed_at"} <= set(md.keys())
    assert md["word_count"] == 2
    assert md["character_count"] == len("Hola mundo")


def test_post_filtra_contenido_inapropiado(client):
    """Palabras bloqueadas se reemplazan por ***."""
    r = client.post("/api/messages", json={
        "message_id": "msg-2",
        "session_id": "s1",
        "content": "hola badword mundo",
        "timestamp": "2025-08-17T20:00:00Z",
        "sender": "user",
    })
    assert r.status_code == 201
    assert r.get_json()["data"]["content"] == "hola *** mundo"


def test_post_timestamp_invalido_retorma_error(client):
    """Timestamp en formato inválido retorna error 400."""
    r = client.post("/api/messages", json={
        "message_id": "msg-3",
        "session_id": "s1",
        "content": "x",
        "timestamp": "2025/08/17 20:00",
        "sender": "user",
    })
    assert r.status_code == 400
    e = r.get_json()["error"]
    assert e["code"] == "INVALID_FORMAT"
    assert isinstance(e["details"], str)


def test_post_invalid_json(client):
    """Body no-JSON retorna INVALID_JSON."""
    r = client.post("/api/messages", data="no json", headers={"Content-Type":"text/plain"})
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "INVALID_JSON"


def test_post_duplicate_message_id_da_409(client):
    """Un message_id duplicado retorna error 409."""
    payload = {
        "message_id": "dup-1",
        "session_id": "s2",
        "content": "x",
        "timestamp": "2025-08-17T20:00:00Z",
        "sender": "user",
    }
    assert client.post("/api/messages", json=payload).status_code == 201
    r = client.post("/api/messages", json=payload)
    assert r.status_code == 409
    assert r.get_json()["error"]["code"] == "DUPLICATE_MESSAGE"


def test_get_por_session_con_paginacion_y_filtro_sender(client):
    """GET lista mensajes filtrando por sender con paginación."""
    for i in range(3):
        client.post("/api/messages", json={
            "message_id": f"g-{i}",
            "session_id": "s3",
            "content": "hola",
            "timestamp": f"2025-08-17T20:00:0{i}Z",
            "sender": "user" if i < 2 else "system",
        })
    r = client.get("/api/messages/s3?sender=user&limit=2&offset=0")
    assert r.status_code == 200
    items = r.get_json()["data"]
    assert len(items) == 2
    assert all(x["sender"] == "user" for x in items)


def test_get_limit_offset_invalidos(client):
    """Parámetros inválidos de paginación retornan error 400."""
    assert client.get("/api/messages/s3?limit=abc&offset=0").status_code == 400
    assert client.get("/api/messages/s3?limit=0&offset=-1").status_code == 400
