# Chat Messages API (Flask + SQLite)
## Descripción General
API REST mínima en Flask + SQLite para almacenar y consultar mensajes de chat por sesión.  
### Funciones clave:
* Crear mensajes: valida campos requeridos, sanea contenido con un filtro básico y agrega metadatos (word_count, character_count, processed_at).
* Listar mensajes por session_id con paginación (limit, offset) y filtro por remitente (sender = user | system).
* Contrato de error consistente con status: "error", code, message y details (string).

**Tecnologías**: Python 3.12+, Flask, sqlite3 (estándar de Python), Pytest para pruebas.

## Instrucciones de configuración
### Requisitos
- Python 3.12.x (Probado)
- pip
### Configuración de palabras bloqueadas
Este proyecto utiliza un archivo `config.json` para definir las palabras que deben ser filtradas.
#### Ejemplo de `config.json`:
```json
{
  "blocked_words": [
    "foo",
    "bar",
    "badword"
  ]
}
```
#### Cómo agregar nuevas palabras
1. Abra el archivo config.json.
2. Edite la lista blocked_words.
3. Guarde los cambios.  
Las palabras que agregue serán tomadas automáticamente por la aplicación en la próxima ejecución.  
### Pasos para ejecutar la API (Localmente)
1. Crear entorno virtual (Luego de clonar el repositorio):  
~~~
python -m venv .venv
~~~
2. Activar el entorno virtual  
      **Linux/macOS**: 
      ~~~
      . .venv/bin/activate
      ~~~
      **Windows (PowerShell)**: 
      ~~~
      .\.venv\Scripts\Activate.ps1
      ~~~
      **Windows (CMD)**: 
      ~~~
      .\.venv\Scripts\activate.bat
      ~~~
3. Instalar dependencias:  
~~~
pip install -r requirements.txt
~~~
4. Ejecutar la API:  
      **Linux/macOS**:  
      ~~~
      export FLASK_APP=app:create_app
      flask run
      ~~~  
      **Windows(CMD)**:  
      ```
      set FLASK_APP=app:create_app
      flask run
      ````
      **Windows(PowerShell)**:  
      ~~~
      $env:FLASK_APP = "app:create_app"
      flask run
      ~~~
5. Base URL por defecto(Local):
~~~
http://127.0.0.1:5000/
~~~
## Documentación de la API
### Health
#### Get `/` 
Devuelve { "ok": true, "time": "<ISO8601>" } para ver si el servicio está vivo.

### Crear mensaje
#### POST `/api/messages`
##### Body(JSON, todos obligatorios):
* message_id: string no vacío.  
* session_id: string no vacío.  
* content: string no vacío.  
* timestamp: string en formato ISO 8601 con zona horaria (ej. 2025-08-17T20:00:00Z o +00:00).  
* sender: string, uno de user o system.  
##### Respuesta 201 (success):
```json
{
  "status": "success",
  "data": {
    "message_id": "...",
    "session_id": "...",
    "content": "...",           // con palabras censuradas si aplica
    "timestamp": "ISO8601",
    "sender": "user|system",
    "metadata": {
      "word_count": 0,
      "character_count": 0,
      "processed_at": "ISO8601"
    }
  }
}
```
##### Errores:
* 400 INVALID_JSON cuando el cuerpo no es JSON válido.  
* 400 INVALID_FORMAT cuando falta un campo o tiene formato inválido (por ejemplo timestamp sin zona). error.details es un string con el detalle.  
* 409 DUPLICATE_MESSAGE cuando message_id ya existe.  
* 500 DB_ERROR ante fallas al persistir.  
##### Ejemplo ```curl```:
~~~
curl -X POST http://127.0.0.1:5000/api/messages -H "Content-Type: application/json" -d "{\"message_id\":\"m1\",\"session_id\":\"s1\",\"content\":\"Hola mundo\",\"timestamp\":\"2025-08-17T20:00:00Z\",\"sender\":\"user\"}"
~~~
### Listar mensajes por sesión
#### GET ```/api/messages/{session_id}```
##### Query params:
* limit: entero en [1..100], por defecto 20.  
* offset: entero ≥ 0, por defecto 0.  
* sender: opcional, user o system.
##### Respuesta 200:
~~~
{
  "status": "success",
  "data": [
    {
      "message_id": "...",
      "session_id": "...",
      "content": "...",
      "timestamp": "ISO8601",
      "sender": "user|system",
      "metadata": {
        "word_count": 0,
        "character_count": 0,
        "processed_at": "ISO8601"
      }
    }
  ]
}
~~~
##### Errores:
* 400 INVALID_FORMAT si limit/offset no son enteros o están fuera de rango, o sender no es válido.  
* 500 DB_ERROR ante fallas al consultar.
##### Ejemplo curl:
~~~
curl "http://127.0.0.1:5000/api/messages/s1?sender=user&limit=10&offset=0"
~~~
### Contrato de error(general):
~~~
{
  "status": "error",
  "error": {
    "code": "INVALID_FORMAT|INVALID_JSON|DUPLICATE_MESSAGE|DB_ERROR",
    "message": "Descripción corta",
    "details": "Detalle específico del error encontrado"
  }
}
~~~
## Instrucciones para pruebas:
1. Ejecutar pruebas unitarias y de integración:  
~~~
python -m pytest
~~~
2. Ejecutar con cobertura (umbral 80%):  
~~~
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=80 --cov-branch
~~~
### Notas:
* Las pruebas con Pytest usan una base de datos temporal
