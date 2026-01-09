# SecurAPI!

## Desarrollando mi propio mini framework para crear rest APIs con python
#### El objetivo del proyecto es educativo: ganar entendimiento sobre como un framework funciona por detrás, aplicar buenas prácticas de seguridad, testing, etc 


### Usage:

##### myapp.py:
```python
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
#### Para aceptar query params en tus endpoints, simplemente agregale parámetro a la función:
```python
@app.add_endpoint("/hola")
def get(query_param):
    return {"response":f"Hola, {query_param}!"}
```
#### Para hacer opcional un parámetro, simplemente agrega un default:
```python
@app.add_endpoint("/hola")
def get(optional_query_param=""):
    return {"response":f"Hola, {optional_query_param}!"}
```
#### Para combinar opcionales y obligatorios, simplemente agregar primero los obligatorios y luegos los opcionales con default:
```python
@app.add_endpoint("/hola")
def get(required_param, optional_query_param=""):
    return {"response":f"Hola, {required_param} {optional_query_param}!"}
```
#### Para leer el body de una request post/put, simplemente agrega en la función el parámetro 'request_body' (agregale un default si queres permitir body vacío):
```python
@app.add_endpoint("/hola/body", "POST)
def get(request_body):
    return {"response":f"Hola, {request_body}"}
```
#### Para devolver un status code HTTP personalizado, simplemente hace que tu endpoint devuelva una tupla con el status code primero:
```python
@app.add_endpoint("/hola/custom-status")
def get(required_param, optional_query_param=""):
    return 200, {"response":f"Hola, {required_param} {optional_query_param}!"}
```
#### Por defecto los metodos aceptados son GET, POST, PUT, DELETE
#### Se puede personalizar pasando como parámetro los metodos que quiero permitir al instanciar la app:
```python
from securapi.main import SecurAPI

app = SecurAPI(allowed_methods={"GET","POST","PUT","PATCH","HEAD","OPTIONS"})

#Este endopoint no va a funcionar porque DELETE no es un metodo permitido:
@app.add_endpoint("/hola", "DELETE")
def delete(required_param, optional_query_param=""):
    return {"response":f"Hola, {required_param} {optional_query_param}!"}

#Este endopoint esta correctamente definido:
@app.add_endpoint("/hola", "OPTIONS")
def options(required_param, optional_query_param=""):
    return {"response":f"Hola, {required_param} {optional_query_param}!"}
```
### Corre el server!
```bash
$uvicorn myapp:app --reload
```

## Rate Limit:
### Disclaimer: hacer rate limiting a nivel de aplicación no es una solucion que proteja tu api de ataques de denegación de servicio (DoS/DDoS) ya que las requests entran al servidor y consumen recursos. Para entornos de produccion deben utilizarse soluciones como CLoudfare, AWS WAF, Nginx, etc, de modo que las requests maliciosas son rechazadas por un proxy/firewall antes de llegar al servidor.

### Implementación de rate-limit a nivel de aplicación:
#### Pasa una instancia del RateLimitMiddleware como parámetro al inicializar SecurAPI:
```python
from securapi.main import SecurAPI
from securapi.security.rateLimiting import RateLimiterMiddleware

rate_limiter = RateLimiterMiddleware(max_requests=60, time_window=60)
app = SecurAPI(rate_limiter=rate_limiter)

@app.add_endpoint("/")
def root():
    return {"response": "Welcome to SecurAPI"}

```
#### En este ejemplo, la aplicación va bloquear una IP que realice más de 60 requests en 60 segundos. 
#### Para ser desbloqueada, la IP debera esperar 60 segundos sin realizar requests.

## Protected endpoints:
### Para proteger endpoints con autenticación, agregar un auth_middleware que reciba un token y devuelva true si esta autorizado:
```python
from securapi.main import SecurAPI

app = SecurAPI()

def auth_middleware_example(token):
    if token == "super-secret-token":
        return True
    return False

@app.add_endpoint("/protected", auth_middleware=auth_middleware_example)
def protected():
    return {"response": "Welcome to the protected route"}

```
#### Securapi va a capturar el auth token en los headers de la request entrante y va a llamar al auth_middleware para validarlo y decidir si dejar pasar la solicitud al endpoint.