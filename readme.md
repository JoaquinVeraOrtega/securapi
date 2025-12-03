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
    return {"status":200, "response":"Hola, get!"}

@app.add_endpoint("/hola","POST")
def post():
    return {"status":200, "response":"Hola, post!"}

@app.add_endpoint("/hola","PUT")
def put():
    return {"status":200, "response":"Hola, put!"}

@app.add_endpoint("/hola","DELETE")
def delete():
    return {"status":200, "response":"Hola, delete!"}
```


##### $uvicorn myapp:app --reload

#### Roadmap:

#### * Query params
#### * Rate limiter
#### * Api key based auth
#### * SQL support
