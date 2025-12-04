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

    @app.add_endpoint("/health", "GET")
    def health():
        return {"status": 200, "response": "OK"}

    @app.add_endpoint("/params", "GET")
    def params_handler(required_param, optional_param="opt"):
        return {
            "status": 200,
            "response": f"Required: {required_param}, Optional: {optional_param}",
        }

    @app.add_endpoint("/echo", "POST")
    def echo(data):
        return {"status": 200, "response": data}

    return app


@pytest.fixture
def running_server(test_app):
    """Fixture that provides a running server"""
    server = ServerManager(test_app, 8000)
    server.start()
    yield server
    server.stop()


class TestSecurAPIIntegration:
    """Integration tests with real HTTP server"""

    def test_health_endpoint(self, running_server):
        """Test basic endpoint"""
        response = httpx.get(f"{running_server.base_url}/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert data["response"] == "OK"

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
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "test"

    def test_404_for_nonexistent_route(self, running_server):
        """Test 404 for non-existent routes"""
        response = httpx.get(f"{running_server.base_url}/nonexistent/")
        assert response.status_code == 404

    def test_method_not_allowed(self, running_server):
        """Test 405 for wrong HTTP method"""
        response = httpx.options(f"{running_server.base_url}/health/")
        assert response.status_code == 405
