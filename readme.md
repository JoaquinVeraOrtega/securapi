# SecurAPI!

## Desarrollando mi propio mini framework para crear rest APIs con python
### Inspirado en FastAPI, claro

#### Usage:

##### myapp.py:
```
from securapi.main import SecurAPI

app = SecurAPI()

@app.add_endpoint("/hola")
def get():
    return {"response":"Hola, get!"}

@app.add_endpoint("/hola","POST")
def post():
    return {"response":"Hola, post!"}

@app.add_endpoint("/hola","PUT")
def put():
    return {"response":"Hola, put!"}

@app.add_endpoint("/hola","DELETE")
def delete():
    return {"response":"Hola, delete!"}
```
#### Para aceptar query params en tus endpoints, simplemente agregale parametros a la funcion:
```
@app.add_endpoint("/hola")
def get(query_param):
    return {"response":f"Hola, {query_param}!"}
```
#### Para hacer opcional un parametro, simplemente agrega un default:
```
@app.add_endpoint("/hola")
def get(optional_query_param=""):
    return {"response":f"Hola, {optional_query_param}!"}
```
#### Para combinar opcionales y obligatorios, simplemente agregar primero los obligatorios y luegos los opcionales con default:
```
@app.add_endpoint("/hola")
def get(required_param, optional_query_param=""):
    return {"response":f"Hola, {required_param} {optional_query_param}!"}
```
#### Para devolver un status code HTTP personalizado, simplemente hace que tu endpoint devuelva una tupla con el status code primero:
@app.add_endpoint("/hola/custom-status")
def get(required_param, optional_query_param=""):
    return 200, {"response":f"Hola, {required_param} {optional_query_param}!"}

##### $uvicorn myapp:app --reload

#### Roadmap:

#### * Query params ✅
#### * Rate limiter ⬛
#### * Api key based auth ⬛
#### * SQL support ⬛
