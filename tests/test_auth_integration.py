import pytest
import httpx
from ..main import SecurAPI
from .testing_server_manager import ServerManager


@pytest.fixture
def test_app():
    """Create a test app with endpoints"""
    app = SecurAPI()

    def auth_middleware(token):
        if token == "valid-token":
            return {"user_id": 1}
        return None
    
    @app.add_endpoint("/")
    def root():
        return {"response": "Welcome to SecurAPI"}

    @app.add_endpoint("/protected", auth_middleware=auth_middleware)
    def protected():
        return {"response": "Welcome to the protected route"}

    return app


@pytest.fixture
def running_server(test_app):
    """Fixture that provides a running server"""
    server = ServerManager(test_app)
    server.start()
    yield server
    server.stop()


class TestAuthIntegration:

    def test_root_endpoint(self, running_server):
        """Test root endpoint"""
        response = httpx.get(f"{running_server.base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Welcome to SecurAPI"

    def test_protected_endpoint_missing_auth(self, running_server):
        """Test protected endpoint"""
        response = httpx.get(f"{running_server.base_url}/protected")
        assert response.status_code == 401
        data = response.json()
        assert data["response"] == "Authentication required"

    def test_protected_endpoint_fail(self, running_server):
        """Test protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = httpx.get(f"{running_server.base_url}/protected", headers=headers)
        assert response.status_code == 401
        data = response.json()
        assert data["response"] == "Authentication required"

    def test_protected_endpoint_success(self, running_server):
        """Test protected endpoint with valid token"""
        headers = {"Authorization": "Bearer valid-token"}
        response = httpx.get(f"{running_server.base_url}/protected", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Welcome to the protected route"