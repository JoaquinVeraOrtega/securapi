import pytest
import httpx
import socket
from ..main import SecurAPI
import uvicorn
from multiprocessing import Process
from ..security.rateLimiting import RateLimiterMiddleware
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
            except (httpx.RequestError, ConnectionError):
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
    rate_limiter = RateLimiterMiddleware(max_requests=3, time_window=5)
    app = SecurAPI(rate_limiter=rate_limiter)

    @app.add_endpoint("/")
    def root():
        return {"response": "Welcome to SecurAPI"}
    
    return app


@pytest.fixture
def running_server(test_app):
    """Fixture that provides a running server"""
    server = ServerManager(test_app)
    server.start()
    yield server
    server.stop()

class TestRateLimiterIntegration:
    def test_rate_limiter_integration(self, running_server):
        base_url = running_server.base_url
        with httpx.Client() as client:
            # First request should be allowed
            response1 = client.get(f"{base_url}/")
            assert response1.status_code == 200
            assert response1.json() == {"response": "Welcome to SecurAPI"}
            
            # Second request should be allowed
            response2 = client.get(f"{base_url}/")
            assert response2.status_code == 200
            assert response2.json() == {"response": "Welcome to SecurAPI"}
            
            # Third request should be blocked due to rate limiting
            response3 = client.get(f"{base_url}/")
            assert response3.status_code == 429  # Assuming 429 for rate limit exceeded
            
            # Wait for time window to expire
            time.sleep(6)
            
            # Next request should be allowed again
            response4 = client.get(f"{base_url}/")
            assert response4.status_code == 200
            assert response4.json() == {"response": "Welcome to SecurAPI"}
            