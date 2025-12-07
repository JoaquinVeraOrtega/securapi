import pytest
import httpx
import socket
from ..main import SecurAPI
import uvicorn
from multiprocessing import Process
import time


def find_free_port():
    """Find a free port to use for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class ServerManager:
    """Helper to manage test server lifecycle"""

    def __init__(self, app, port=None):
        self.app = app
        self.port = port or find_free_port()
        self.process = None
        self.base_url = f"http://127.0.0.1:{self.port}"

    def start(self):
        """Start server in background"""

        def run():
            uvicorn.run(
                app=self.app,
                host="127.0.0.1",
                port=self.port,
                log_level="error",
                access_log=False,
            )

        self.process = Process(target=run)
        self.process.start()
        self._wait_for_server()

    def _wait_for_server(self, timeout=10):
        """Wait for server to be ready"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                httpx.get(f"{self.base_url}/", timeout=0.5)
                return
            except:
                time.sleep(0.1)
        raise TimeoutError(f"Server didn't start in {timeout} seconds")

    def stop(self):
        """Stop server"""
        if self.process:
            self.process.terminate()
            self.process.join(timeout=5)


@pytest.fixture
def test_app():
    """Create a test app with endpoints"""
    app = SecurAPI()

    @app.add_endpoint("/", "GET")
    def root():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/health", "GET")
    def health():
        return {"response": "OK"}

    @app.add_endpoint("/health", "PUT")
    def put_health():
        return {"response": "OK put"}

    @app.add_endpoint("/health", "DELETE")
    def delete_health():
        return None

    @app.add_endpoint("/health", "POST")
    def post_health():
        return {"response": "OK post"}

    @app.add_endpoint("/custom-status", "GET")
    def custom_status():
        return 201, {"response": "Accepted"}

    @app.add_endpoint("/custom-status-invalid", "GET")
    def custom_status_invalid():
        return 2037842, {"response": "Accepted"}

    @app.add_endpoint("/delete/responsebody/", "DELETE")
    def delete_with_content():
        return 200, {"response": "Deleted"}

    @app.add_endpoint("/params", "GET")
    def params_handler(required_param, optional_param="opt"):
        return {
            "response": f"Required: {required_param}, Optional: {optional_param}",
        }

    @app.add_endpoint("/echo", "POST")
    def echo(data):
        return {"response": data}

    @app.add_endpoint("/body", "POST")
    def request_body_post_handler(request_body):
        return {"response": f"Request body received: {request_body}"}

    @app.add_endpoint("/body", "PUT")
    def request_body_put_handler(request_body):
        return {"response": f"Request body received: {request_body}"}

    @app.add_endpoint("/body/params", "POST")
    def request_body_and_query_params_post_handler(
        request_body, required_qparam, optional_qparam="optional"
    ):
        return {
            "response": {
                "Request body received": request_body,
                "optional_qparam": optional_qparam,
                "required_qparam": required_qparam,
            }
        }

    @app.add_endpoint("/body/params", "PUT")
    def request_body_and_query_params_put_handler(
        request_body, required_qparam, optional_qparam="optional"
    ):
        return {
            "response": {
                "Request body received": request_body,
                "optional_qparam": optional_qparam,
                "required_qparam": required_qparam,
            }
        }

    @app.add_endpoint("/body/params/optional-body", "POST")
    def optional_request_body_handler(
        request_body="default body",
    ):
        return {
            "response": {
                "Request body received": request_body,
            }
        }
    @app.add_endpoint("/spanish", "GET")
    def spanish_endpoint():
        return {"response": "¡Hola! Niño español"}  # ñ = 2 bytes in UTF-8

    @app.add_endpoint("/emoji", "GET")
    def emoji_endpoint():
        return {"response": "Hello 🎉 World"}  # 🎉 = 4 bytes in UTF-8

    @app.add_endpoint("/chinese", "GET")
    def chinese_endpoint():
        return {"response": "你好世界"}  # Each char = 3 bytes in UTF-8

    @app.add_endpoint("/price", "GET")
    def price_endpoint():
        return {"response": "Price: €99.99"}
    
    return app


@pytest.fixture
def running_server(test_app):
    """Fixture that provides a running server"""
    server = ServerManager(test_app, 8000)
    server.start()
    yield server
    server.stop()


class TestSecurAPIIntegrationMethods:
    """Integration tests with real HTTP server"""

    def test_root_endpoint(self, running_server):
        """Test root endpoint"""
        response = httpx.get(f"{running_server.base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Welcome to SecurAPI"

    def test_health_endpoint(self, running_server):
        """Test basic endpoint"""
        response = httpx.get(f"{running_server.base_url}/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "OK"

    def test_same_path_different_methods(self, running_server):
        """Test same path with different HTTP methods"""
        get_response = httpx.get(f"{running_server.base_url}/health/")
        post_response = httpx.post(f"{running_server.base_url}/health/")
        put_response = httpx.put(f"{running_server.base_url}/health/")
        delete_response = httpx.delete(f"{running_server.base_url}/health/")

        assert get_response.status_code == 200
        assert post_response.status_code == 201
        assert put_response.status_code == 200
        assert delete_response.status_code == 204

        get_response = httpx.get(f"{running_server.base_url}/health")
        post_response = httpx.post(f"{running_server.base_url}/health")
        put_response = httpx.put(f"{running_server.base_url}/health")
        delete_response = httpx.delete(f"{running_server.base_url}/health")

        assert get_response.status_code == 200
        assert post_response.status_code == 201
        assert put_response.status_code == 200
        assert delete_response.status_code == 204

        assert get_response.json() != post_response.json() != put_response.json()
        assert delete_response.content == b""

    def test_delete_with_content(self, running_server):
        """Test DELETE endpoint returns no content"""
        response = httpx.delete(f"{running_server.base_url}/delete/responsebody/")
        assert response.status_code == 200
        assert response.json()["response"] == "Deleted"

class TestSecurAPIIntegrationParams:
    """Integration tests for query parameters"""

    def test_missing_required_param(self, running_server):
        """Test missing required parameter"""
        response = httpx.get(f"{running_server.base_url}/params/")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "required parameters" in data["error"].lower()

    def test_with_required_param(self, running_server):
        """Test with required parameter"""
        response = httpx.get(
            f"{running_server.base_url}/params/", params={"required_param": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Required: test, Optional: opt"

    def test_with_both_params(self, running_server):
        """Test with both required and optional parameters"""
        response = httpx.get(
            f"{running_server.base_url}/params/",
            params={"required_param": "req", "optional_param": "custom"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Required: req, Optional: custom"

    def test_param_order_independence(self, running_server):
        """Test that parameter order doesn't matter"""
        response1 = httpx.get(
            f"{running_server.base_url}/params/",
            params={"required_param": "first", "optional_param": "second"},
        )
        response2 = httpx.get(
            f"{running_server.base_url}/params/",
            params={"optional_param": "second", "required_param": "first"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_post_endpoint(self, running_server):
        """Test POST endpoint"""
        response = httpx.post(
            f"{running_server.base_url}/echo/", params={"data": "test"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == "test"

    def test_404_for_nonexistent_route(self, running_server):
        """Test 404 for non-existent routes"""
        response = httpx.get(f"{running_server.base_url}/nonexistent/")
        assert response.status_code == 404

class TestSecurAPIIntegrationStatusCodes:
    """Integration tests for custom status codes"""

    def test_custom_status_code(self, running_server):
        """Test endpoint returning custom status code"""
        response = httpx.get(f"{running_server.base_url}/custom-status/")
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == "Accepted"

    def test_custom_status_code_invalid(self, running_server):
        """Test endpoint returning custom status code"""
        response = httpx.get(f"{running_server.base_url}/custom-status-invalid/")
        assert response.status_code == 500
        data = response.json()
        assert data["response"] == "Server Error"

class TestSecurAPIIntegrationRequestBody:
    """Integration tests for request body handling"""

    def test_request_body_post(self, running_server):
        """Test POST endpoint with request body"""
        response = httpx.post(
            f"{running_server.base_url}/body/", content="Test body content"
        )
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == "Request body received: Test body content"

    def test_request_body_put(self, running_server):
        """Test PUT endpoint with request body"""
        response = httpx.put(
            f"{running_server.base_url}/body/", content="Test body content"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Request body received: Test body content"

    def test_request_body_post_and_rparams(self, running_server):
        """Test POST endpoint with request body"""
        response = httpx.post(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={"required_qparam": "required"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == {
            "Request body received": "Test body content",
            "optional_qparam": "optional",
            "required_qparam": "required",
        }

    def test_request_body_put_and_rparams(self, running_server):
        """Test PUT endpoint with request body"""
        response = httpx.put(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={"required_qparam": "required"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == {
            "Request body received": "Test body content",
            "optional_qparam": "optional",
            "required_qparam": "required",
        }

    def test_request_body_post_and_params(self, running_server):
        """Test POST endpoint with request body"""
        response = httpx.post(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={"optional_qparam": "opt", "required_qparam": "required"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == {
            "Request body received": "Test body content",
            "optional_qparam": "opt",
            "required_qparam": "required",
        }

        response = httpx.post(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={"optional_qparam": "opt"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data == {"error": "Missing required parameters"}

        response = httpx.post(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={
                "optional_qparam": "opt",
                "required_qparam": "required",
                "invalid_param": "oops",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "is not a valid parameter" in data["error"]

    def test_request_body_put_and_params(self, running_server):
        """Test PUT endpoint with request body"""
        response = httpx.put(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={"optional_qparam": "opt", "required_qparam": "required"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == {
            "Request body received": "Test body content",
            "optional_qparam": "opt",
            "required_qparam": "required",
        }

        response = httpx.put(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={"optional_qparam": "opt"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data == {"error": "Missing required parameters"}
   
        response = httpx.put(
            f"{running_server.base_url}/body/params/",
            content="Test body content",
            params={
                "optional_qparam": "opt",
                "required_qparam": "required",
                "invalid_param": "oops",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "is not a valid parameter" in data["error"]
    
    def test_optional_request_body_post(self, running_server):
        """Test POST endpoint with optional request body"""
        response = httpx.post(
            f"{running_server.base_url}/body/params/optional-body/",
            content="Provided body content",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == {
            "Request body received": "Provided body content",
        }

        response = httpx.post(
            f"{running_server.base_url}/body/params/optional-body/",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["response"] == {
            "Request body received": "default body",
         }
        
    def test_required_request_body_missing(self, running_server):
        """Test POST endpoint with missing required request body"""
        response = httpx.post(
            f"{running_server.base_url}/body/",
        )
        assert response.status_code == 400
        data = response.json()
        assert data == {"error": "Missing required request body"}


class TestSecurAPIIntegrationContentLengthEncoding:
    """Integration tests for content with multi-byte UTF-8 characters"""

    def test_spanish_endpoint(self, running_server):
        """Test endpoint with Spanish characters"""
        response = httpx.get(f"{running_server.base_url}/spanish/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "¡Hola! Niño español"

    def test_emoji_endpoint(self, running_server):
        """Test endpoint with emoji characters"""
        response = httpx.get(f"{running_server.base_url}/emoji/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello 🎉 World"

    def test_chinese_endpoint(self, running_server):
        """Test endpoint with Chinese characters"""
        response = httpx.get(f"{running_server.base_url}/chinese/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "你好世界"

    def test_price_endpoint(self, running_server):
        """Test endpoint with Euro symbol"""
        response = httpx.get(f"{running_server.base_url}/price/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Price: €99.99"

@pytest.fixture
def test_app_with_extra_config():
    """Create a test app with endpoints"""
    allowed_methods = {"PATCH", "HEAD", "OPTIONS"}
    app = SecurAPI(allowed_methods=allowed_methods)

    @app.add_endpoint("/get", "GET")
    def get():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/post", "POST")
    def post():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/put", "PUT")
    def put ():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/delete", "DELETE")
    def delete():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/patch", "PATCH")
    def patch():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/options", "OPTIONS")
    def options():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/head", "HEAD")
    def head():
        return {"response": "Welcome to SecurAPI"}
    
    return app


@pytest.fixture
def running_server_extra_config(test_app_with_extra_config):
    """Fixture that provides a running server"""
    server = ServerManager(test_app_with_extra_config, 8000)
    server.start()
    yield server
    server.stop()

class TestSecurAPIIntegrationMethodsExtraConfig:
    """Integration tests with real HTTP server"""

    def test_method_not_allowed(self, running_server_extra_config):
        """Test 405 for wrong HTTP method"""
        response = httpx.get(f"{running_server_extra_config.base_url}/get")
        assert response.status_code == 405
        response = httpx.post(f"{running_server_extra_config.base_url}/post")
        assert response.status_code == 405
        response = httpx.put(f"{running_server_extra_config.base_url}/put")
        assert response.status_code == 405
        response = httpx.delete(f"{running_server_extra_config.base_url}/delete")
        assert response.status_code == 405

    def test_configured_methods_allowed(self, running_server_extra_config):
        """Test root endpoint"""
        response = httpx.options(f"{running_server_extra_config.base_url}/options")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Welcome to SecurAPI"

        response = httpx.patch(f"{running_server_extra_config.base_url}/patch")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Welcome to SecurAPI"

        response = httpx.head(f"{running_server_extra_config.base_url}/head")
        assert response.status_code == 200
        assert response.content == b""