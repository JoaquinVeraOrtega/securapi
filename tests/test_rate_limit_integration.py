import pytest
import httpx
from ..main import SecurAPI
from ..security.rateLimiting import RateLimiterMiddleware
from .testing_server_manager import ServerManager
import time

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
            