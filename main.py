from typing import Callable


class SecurAPI:

    routes = {
        "GET": {},
        "POST": {},
        "PUT": {},
        "DELETE": {},
    }

    allowed_methods = ("GET", "POST", "PUT", "DELETE")

    def __init__(self) -> None:
        print("Welcome to SecurAPI")
        print("Faster than FastAPI!")
        print("...")
        print("Ok, not really...")

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

            if method not in self.allowed_methods:
                await self.method_not_allowed(method, send)
                return
            if not self.is_valid_route(path, method):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,  # Not found
                        "headers": [
                            (b"content-type", b"text/plain"),
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
                await self.router(method, path, send)

        except ValueError as e:
            print(e)
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,  # BAD request
                    "headers": [
                        (b"content-type", b"text/plain"),
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

    async def router(self, method, path, send):
        try:
            response = self.routes[method][path]()
            status_code = response["status"]
            if not isinstance(status_code, int):
                raise TypeError("Status code MUST be an integer")
            body = response["response"]
            content_length = str(len(body))
            await send(
                {
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": [
                        (b"content-type", b"text/plain"),
                        (b"content-length", content_length.encode()),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body.encode(),
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
                    (b"content-type", b"text/plain"),
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

    async def method_not_allowed(self, method, send):
        await send(
            {
                "type": "http.response.start",
                "status": 400,  # BAD request
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"content-length", b"49"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"ERROR: only get/post/put/delete requests accepted",
            }
        )

    # Endpoints decorators:
    def add_endpoint(self, path: str, method: str = "GET"):
        """Add endpoint (default: GET). The return must be a dict with this fields: {"status": httpstatusCode, "response": responseBody(optional)}"""

        def decorator(handler: Callable):
            self.routes[method][path] = handler
            return handler

        return decorator