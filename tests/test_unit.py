from ..main import SecurAPI

class TestSecurAPIUnit:
    def test_securapi_initialization(self):
        app = SecurAPI()
        assert isinstance(app, SecurAPI)
        assert app.allowed_methods == {"GET", "POST", "PUT", "DELETE"}
        for method in app.allowed_methods:
            assert method in app.routes
            assert isinstance(app.routes[method], dict)

    def test_securapi_init_with_config(self):
        allowed_methods = {"PATCH", "HEAD", "OPTIONS"}
        app = SecurAPI(allowed_methods=allowed_methods)
        assert app.allowed_methods == {"PATCH", "HEAD", "OPTIONS"}
        for method in app.allowed_methods:
            assert method in app.routes
            assert isinstance(app.routes[method], dict)
        for method in ("GET", "POST", "PUT", "DELETE"):
            assert method not in app.allowed_methods
            assert method not in app.routes

    def test_securapi_init_with_wrong_config(self):
        allowed_methods = {"INVALID", "METHOD", "123"}
        app = SecurAPI(allowed_methods=allowed_methods)
        assert app.allowed_methods == {"GET", "POST", "PUT", "DELETE"}
        for method in app.allowed_methods:
            assert method in app.routes
            assert isinstance(app.routes[method], dict)
        for method in allowed_methods:
            assert method not in app.allowed_methods
            assert method not in app.routes

    def test_is_valid_route(self):
        app = SecurAPI()
        @app.add_endpoint("/test", "GET")
        def test_handler():
            return {"status": 200, "response": "Test"}
        assert app.is_valid_route("/test/", "GET") is True
        assert app.is_valid_route("/test", "GET") is False
        assert app.is_valid_route("/invalid", "GET") is False
        assert app.is_valid_route("/invalid/", "GET") is False
        assert app.is_valid_route("/test", "POST") is False
        assert app.is_valid_route("/test/", "POST") is False


    def test_add_endpoint(self):
        app = SecurAPI()
        @app.add_endpoint("/sample", "POST")
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




