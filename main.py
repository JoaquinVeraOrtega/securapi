import inspect
from typing import Callable
from .endpoints import Endpoint
import json

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

    async def request_manager(self, scope, recieve, send):
        try:
            if scope["type"] not in ["http", "lifespan"]:
                raise ValueError(
                    f"Expected HTTP scope, got {scope['type']}."
                    "Only HTTP requests are supported."
                )
            method = scope["method"]
            path = scope["path"]
            q_params = scope["query_string"].decode()

            if method not in self.allowed_methods:
                await self.bad_request({"status": 405,"error": f"only {self.allowed_methods} requests accepted"}, send)
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
                await self.router(method, path, q_params, send)

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

    async def router(self, method, path, q_params, send):
        try:
            endpoint: Endpoint = self.routes[method][path]
            
            if endpoint.params:
                response_params = endpoint.update_params(q_params)
                if isinstance(response_params, dict):
                    if inspect.iscoroutinefunction(endpoint.handler):
                        response = await endpoint.handler(**response_params)
                    else:
                        response = endpoint.handler(**response_params)
                else:
                    await self.bad_request({"status": 400, "error": response_params}, send)
                    return
            else:
                if inspect.iscoroutinefunction(endpoint.handler):
                    response = await endpoint.handler()
                else:
                    response = endpoint.handler()

            status_code = response["status"]
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
        except TypeError as e:
            print(e)
        except KeyError as e:
            print(f"Key error: the response dict MUST contain a {e} field")
        await send(
            {
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", b"5"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"ERROR",
            }
        )

    async def bad_request(self, messaje: dict, send):
        response_body = json.dumps(messaje)
        await send(
            {
                "type": "http.response.start",
                "status": messaje["status"],  # BAD request
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
            if not path.endswith("/"):
                formated_path = path + "/"
            endpoint = Endpoint(handler, argspec, method, formated_path)
            self.routes[method][formated_path] = endpoint

        return decorator
