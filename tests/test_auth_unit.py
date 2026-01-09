from ..main import SecurAPI

class TestAuthUnit:
    def test_add_endpoint_auth(self):
        app = SecurAPI()
        @app.add_endpoint("/sample", "POST", auth_middleware=lambda token: {"user_id": 1} if token == "valid-token" else None)
        def sample_handler(param1, request_body, param2="default"):
            return {"status": 200, "response": f"Param1: {param1}, Param2: {param2}"}
        assert app.is_valid_route("/sample/", "POST") is True
        endpoint = app.routes["POST"]["/sample/"]
        assert endpoint.method == "POST"
        assert endpoint.path == "/sample/"
        assert "param1" in endpoint.params
        assert "param2" in endpoint.params
        assert endpoint.params["param2"] == "default"
        assert "param1" in endpoint.required_params
        assert "param2" not in endpoint.required_params
        assert endpoint.request_body is True
        assert endpoint.body_required is True
        assert endpoint.auth_middleware is not None