import inspect
from typing import Callable
from .endpoints import Endpoint
import json
from http import HTTPStatus

    
class SecurAPI:

    def __init__(self) -> None:
            self.routes = {m: {} for m in ("GET", "POST", "PUT", "DELETE")}
            self.allowed_methods = ("GET", "POST", "PUT", "DELETE")
            print("+----------------------+")
            print("| Welcome to SecurAPI  |")
            print("| Faster than FastAPI! |")
            print("| .....                |")
            print("| Ok, not really...    |")
            print("+----------------------+")

    def __call__(self, scope):
        """ASGI interface - returns a coroutine that takes (receive, send)"""

        async def asgi_wrapper(receive, send):
            return await self.request_manager(scope, receive, send)

        return asgi_wrapper

    def is_valid_route(self, path, method) -> bool:
        if path not in self.routes[method]:
            return False
        return True

    async def request_manager(self, scope, receive, send):
        try:
            if scope["type"] not in ["http", "lifespan"]:
                raise ValueError(
                    f"Expected HTTP scope, got {scope['type']}."
                    "Only HTTP requests are supported."
                )
            method = scope["method"]
            path = scope["path"]
            if not path.endswith("/"):
                path += "/"
            q_params = scope["query_string"].decode()

            if method not in self.allowed_methods:
                await self.bad_request(405,{"error": f"only {self.allowed_methods} requests accepted"}, send)
                return
            if not self.is_valid_route(path, method):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,  # Not found
                        "headers": [
                            (b"content-type", b"application/json"),
                            (
                                b"content-length",
                                str(len(path) + len("Path:  not found")).encode(),
                            ),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": f"Path: {path} not found".encode(),
                    }
                )
            else:
                await self.router(method, path, q_params, receive, send)

        except ValueError as e:
            print(e)
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,  # BAD request
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", b"34"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"ERROR: only http requests accepted",
                }
            )


    async def router(self, method, path, q_params, receive, send):
        default_status = {"GET": 200, "POST": 201, "PUT": 200, "DELETE": 204}

        try:
            endpoint: Endpoint = self.routes[method][path]
            args = {}
            if endpoint.request_body or endpoint.params:
                if endpoint.params:
                    response_params = endpoint.update_params(q_params)
                    if isinstance(response_params, dict):
                        args = response_params
                    else:
                        await self.bad_request(400, {"error": response_params}, send)
                        return
                if endpoint.request_body:
                    request_body = (await read_body(receive)).decode()
                    print(f"Request body: {request_body}")
                    print(endpoint.body_required)
                    if not request_body and endpoint.body_required:
                        await self.bad_request(400, {"error": "Missing required request body"}, send)
                        return                            
                    elif request_body:
                        args["request_body"] = request_body
                 
                if inspect.iscoroutinefunction(endpoint.handler):
                    response = await endpoint.handler(**args)
                else:
                    response = endpoint.handler(**args)                    
            else:
                if inspect.iscoroutinefunction(endpoint.handler):
                    response = await endpoint.handler()
                else:
                    response = endpoint.handler()
            if isinstance(response, tuple):
                status_code = response[0]
                if not valid_status_code(status_code):
                    raise Exception("Invalid HTTP status code returned by endpoint")
                response_body = json.dumps(response[1])
            else:
                status_code = default_status[method]
                response_body = json.dumps(response)

            if not isinstance(status_code, int):
                raise TypeError("Status code MUST be an integer")
            content_length = str(len(response_body))
            await send(
                {
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", content_length.encode()),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": response_body.encode(),
                }
            )
            return
        except (TypeError, KeyError, Exception) as e:
            print(e)
            await self.internal_error(send)


    async def internal_error(self, send):
        await send(
            {
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", b"27"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"response":"Server Error"}',
            }
        )

    async def bad_request(self, status_code: int, message: dict, send):
        response_body = json.dumps(message)
        await send(
            {
                "type": "http.response.start",
                "status": status_code,  # BAD request
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(response_body)).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response_body.encode(),
            }
        )

    # Endpoints decorators:
    def add_endpoint(self, path: str, method: str = "GET"):
        """Add endpoint (default: GET).\n
        The return must be a dict with this fields: {"status": httpstatusCode, "response": responseBody}\n
        To accept query params, add parameters to the function.\n
        To make the query params optional, add a default to the parameter"""

        def decorator(handler: Callable):
            formated_path = path
            argspec = inspect.getfullargspec(handler)
            body_required = False
            if "request_body" in argspec.args:
                sig = inspect.signature(handler)
                params = sig.parameters
                r_body = params["request_body"]
                body_required = r_body.default == inspect.Parameter.empty
            if not path.endswith("/"):
                formated_path = path + "/"
            endpoint = Endpoint(handler, argspec, method, body_required, formated_path)
            self.routes[method][formated_path] = endpoint

        return decorator

def valid_status_code(status_code: int) -> bool:
    """Validate if status code is a valid HTTP status code"""
    try:
        # This will raise ValueError for invalid codes
        HTTPStatus(status_code)
        return True
    except ValueError:
        return False

async def read_body(receive):
    """
    Read and return the entire body from an incoming ASGI message.
    """
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return body