import inspect
from typing import Callable
from .endpoints import Endpoint
import json
from http import HTTPStatus
import logging
from .security.rateLimitting import RateLimiterMiddleware, RateLimitException

class SecurAPI:

    def __init__(self, allowed_methods=None, rate_limiter=None) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            self.logger.addHandler(ch)
        if allowed_methods is not None:
            if all(valid_method(m) for m in allowed_methods):
                self.allowed_methods = allowed_methods
            else:
                self.allowed_methods = {"GET", "POST", "PUT", "DELETE"}
                self.logger.warning(
                    "One or more invalid HTTP methods provided. Using default methods: GET, POST, PUT, DELETE"
                )
        else:
            self.allowed_methods = {"GET", "POST", "PUT", "DELETE"}
        self.routes = {m: {} for m in self.allowed_methods}
        self.logger.info("SecurAPI initialized")
        if rate_limiter is not None and isinstance(rate_limiter, RateLimiterMiddleware):
            self.rate_limiter = rate_limiter
        else:
            self.rate_limiter = None

    def __call__(self, scope):
        """ASGI interface - returns a coroutine that takes (receive, send)"""

        async def asgi_wrapper(receive, send):
            return await self.request_manager(scope, receive, send)

        return asgi_wrapper

    def is_valid_route(self, path, method) -> bool:
        return path in self.routes[method]

    async def request_manager(self, scope, receive, send):
        try:
            if self.rate_limiter is not None and scope["type"] == "http":
                
                if not self.rate_limiter.new_request_allowed(scope["client"][0]):
                    raise RateLimitException("Rate limit exceeded")
            if scope["type"] not in ["http", "lifespan"]:
                raise ValueError(
                    f"Expected HTTP scope, got {scope['type']}."
                    "Only HTTP requests are supported."
                )
            method = scope["method"].upper()
            path = scope["path"]
            if not path.endswith("/"):
                path += "/"
            q_params = scope["query_string"].decode()

            if method not in self.allowed_methods:
                await self.bad_request(
                    405,
                    {"error": f"only {', '.join(self.allowed_methods)} requests accepted"},
                    send,
                )
                return
            if not self.is_valid_route(path, method):
                response_body = json.dumps({"error": f"Path {path} not found"})
                content_length = str(len(response_body.encode("utf-8")))
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,  # Not found
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", content_length.encode()),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": response_body.encode("utf-8"),
                    }
                )
            else:
                await self.router(method, path, q_params, receive, send)
        except RateLimitException as e:
            self.logger.warning(e)
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,  # Too many requests
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", b"26"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"ERROR: Rate limit exceeded",
                }
            )
        except ValueError as e:
            self.logger.exception(e)
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
        default_status = {
            "GET": 200,
            "POST": 201,
            "PUT": 200,
            "DELETE": 204,
            "PATCH": 200,
            "HEAD": 200,
            "OPTIONS": 200,
        }

        try:
            endpoint: Endpoint = self.routes[method][path]
            args = {}
            if endpoint.request_body or endpoint.params:
                if endpoint.params:
                    response_params = endpoint.update_params(q_params)
                    args = response_params
                if endpoint.request_body:
                    request_body = (await read_body(receive)).decode("utf-8")
                    if not request_body and endpoint.body_required:
                        await self.bad_request(
                            400, {"error": "Missing required request body"}, send
                        )
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
                    raise ValueError("Invalid HTTP status code returned by endpoint")
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
        except (ValueError, TypeError, KeyError) as e:
            self.logger.exception(e)
            if isinstance(e, ValueError) and "Invalid HTTP status code" in str(e):
                await self.internal_error(send)
            else:
                await self.bad_request(400, {"error": str(e)}, send)

    async def internal_error(self, send) -> None:
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
        response_bytes = response_body.encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(response_bytes)).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response_bytes,
            }
        )

    # Endpoints decorators:
    def add_endpoint(self, path: str, method: str = "GET") -> Callable:
        """Add endpoint (default: GET).\n
        The return must be a dict with this fields: {"status": httpstatusCode, "response": responseBody}\n
        To accept query params, add parameters to the function.\n
        To make the query params optional, add a default to the parameter"""

        def decorator(handler: Callable):
            try:
                if method not in self.allowed_methods:
                    raise ValueError(
                        f"Method {method} not allowed. Allowed methods: {self.allowed_methods}"
                    )
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
                endpoint = Endpoint(
                    handler, argspec, method, body_required, formated_path
                )
                self.routes[method][formated_path] = endpoint
                return handler
            except ValueError as e:
                self.logger.info(f"Error adding endpoint {handler.__name__}: {e}")
                return handler

        return decorator


def valid_status_code(status_code: int) -> bool:
    """Validate if status code is a valid HTTP status code"""
    try:
        # This will raise ValueError for invalid codes
        HTTPStatus(status_code)
        return True
    except ValueError:
        return False


def valid_method(method: str) -> bool:
    """Validate if method is a valid HTTP method"""
    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    return method.upper() in valid_methods


async def read_body(receive) -> bytes:
    """
    Read and return the entire body from an incoming ASGI message.
    """
    body = b""
    more_body = True
    MAX_BODY_SIZE = 1024 * 1024  # 1MB limit
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
        if len(body) > MAX_BODY_SIZE:
            raise ValueError("Request body too large")
    return body
