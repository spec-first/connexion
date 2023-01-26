import json
import logging
import pathlib

import pytest
from connexion import App
from connexion.resolver import MethodResolver, MethodViewResolver
from connexion.security import SecurityHandlerFactory
from starlette.types import Receive, Scope, Send
from werkzeug.test import Client, EnvironBuilder

logging.basicConfig(level=logging.INFO)

TEST_FOLDER = pathlib.Path(__file__).parent
FIXTURES_FOLDER = TEST_FOLDER / "fixtures"
SPEC_FOLDER = TEST_FOLDER / "fakeapi"
OPENAPI2_SPEC = ["swagger.yaml"]
OPENAPI3_SPEC = ["openapi.yaml"]
SPECS = OPENAPI2_SPEC + OPENAPI3_SPEC
METHOD_VIEW_RESOLVERS = [MethodResolver, MethodViewResolver]


class FakeResponse:
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: ste
        """
        self.status_code = status_code
        self.text = text
        self.ok = status_code == 200

    def json(self):
        return json.loads(self.text)


def fixed_get_environ():
    """See https://github.com/pallets/werkzeug/issues/2347"""

    original_get_environ = EnvironBuilder.get_environ

    def f(self):
        result = original_get_environ(self)
        result.pop("HTTP_CONTENT_TYPE", None)
        result.pop("HTTP_CONTENT_LENGTH", None)
        return result

    return f


EnvironBuilder.get_environ = fixed_get_environ()


def buffered_open():
    """For use with ASGI middleware"""

    original_open = Client.open

    def f(*args, **kwargs):
        kwargs["buffered"] = True
        return original_open(*args, **kwargs)

    return f


Client.open = buffered_open()


# Helper fixtures functions
# =========================


@pytest.fixture
def oauth_requests(monkeypatch):
    class FakeClient:
        @staticmethod
        async def get(url, params=None, headers=None, timeout=None):
            """
            :type url: str
            :type params: dict| None
            """
            headers = headers or {}
            if url == "https://oauth.example/token_info":
                token = headers.get("Authorization", "invalid").split()[-1]
                if token in ["100", "has_myscope"]:
                    return FakeResponse(
                        200, '{"uid": "test-user", "scope": ["myscope"]}'
                    )
                if token in ["200", "has_wrongscope"]:
                    return FakeResponse(
                        200, '{"uid": "test-user", "scope": ["wrongscope"]}'
                    )
                if token == "has_myscope_otherscope":
                    return FakeResponse(
                        200, '{"uid": "test-user", "scope": ["myscope", "otherscope"]}'
                    )
                if token in ["300", "is_not_invalid"]:
                    return FakeResponse(404, "")
                if token == "has_scopes_in_scopes_with_s":
                    return FakeResponse(
                        200, '{"uid": "test-user", "scopes": ["myscope", "otherscope"]}'
                    )
            return url

    monkeypatch.setattr(SecurityHandlerFactory, "client", FakeClient())


@pytest.fixture
def security_handler_factory():
    security_handler_factory = SecurityHandlerFactory()
    yield security_handler_factory


@pytest.fixture
def app():
    cnx_app = App(__name__, specification_dir=SPEC_FOLDER)
    cnx_app.add_api("api.yaml", validate_responses=True)
    return cnx_app


@pytest.fixture
def simple_api_spec_dir():
    return FIXTURES_FOLDER / "simple"


@pytest.fixture
def problem_api_spec_dir():
    return FIXTURES_FOLDER / "problem"


@pytest.fixture
def secure_api_spec_dir():
    return FIXTURES_FOLDER / "secure_api"


@pytest.fixture
def default_param_error_spec_dir():
    return FIXTURES_FOLDER / "default_param_error"


@pytest.fixture
def json_validation_spec_dir():
    return FIXTURES_FOLDER / "json_validation"


@pytest.fixture(scope="session")
def json_datetime_dir():
    return FIXTURES_FOLDER / "datetime_support"


def build_app_from_fixture(
    api_spec_folder, spec_file="openapi.yaml", middlewares=None, **kwargs
):
    debug = True
    if "debug" in kwargs:
        debug = kwargs["debug"]
        del kwargs["debug"]

    cnx_app = App(
        __name__,
        specification_dir=FIXTURES_FOLDER / api_spec_folder,
        middlewares=middlewares,
    )

    cnx_app.add_api(spec_file, **kwargs)
    cnx_app._spec_file = spec_file
    return cnx_app


@pytest.fixture(scope="session", params=SPECS)
def simple_app(request):
    return build_app_from_fixture("simple", request.param, validate_responses=True)


@pytest.fixture(scope="session", params=OPENAPI3_SPEC)
def simple_openapi_app(request):
    return build_app_from_fixture("simple", request.param, validate_responses=True)


@pytest.fixture(scope="session", params=SPECS)
def reverse_proxied_app(request):
    class ReverseProxied:
        def __init__(self, app, root_path=None, scheme=None, server=None):
            self.app = app
            self.root_path = root_path
            self.scheme = scheme
            self.server = server

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            logging.warning(
                "this demo is not secure by default!! "
                "You'll want to make sure these headers are coming from your proxy, "
                "and not directly from users on the web!"
            )
            root_path = scope.get("root_path") or self.root_path
            for header, value in scope.get("headers", []):
                if header == b"x-forwarded-path":
                    root_path = value.decode()
                    break
            if root_path:
                scope["root_path"] = "/" + root_path.strip("/")
                path_info = scope.get("PATH_INFO", scope.get("path"))
                if path_info.startswith(root_path):
                    scope["PATH_INFO"] = path_info[len(root_path) :]

            scope["scheme"] = scope.get("scheme") or self.scheme
            scope["server"] = scope.get("server") or (self.server, None)

            return await self.app(scope, receive, send)

    app = build_app_from_fixture("simple", request.param, validate_responses=True)
    app.middleware = ReverseProxied(app.middleware, root_path="/reverse_proxied/")
    return app


@pytest.fixture(scope="session", params=SPECS)
def snake_case_app(request):
    return build_app_from_fixture(
        "snake_case", request.param, validate_responses=True, pythonic_params=True
    )


@pytest.fixture(scope="session", params=SPECS)
def invalid_resp_allowed_app(request):
    return build_app_from_fixture("simple", request.param, validate_responses=False)


@pytest.fixture(scope="session", params=SPECS)
def strict_app(request):
    return build_app_from_fixture(
        "simple", request.param, validate_responses=True, strict_validation=True
    )


@pytest.fixture(scope="session", params=SPECS)
def problem_app(request):
    return build_app_from_fixture("problem", request.param, validate_responses=True)


@pytest.fixture(scope="session", params=SPECS)
def schema_app(request):
    return build_app_from_fixture(
        "different_schemas", request.param, validate_responses=True
    )


@pytest.fixture(scope="session", params=SPECS)
def secure_endpoint_app(request):
    return build_app_from_fixture(
        "secure_endpoint",
        request.param,
        validate_responses=True,
    )


@pytest.fixture(scope="session", params=SPECS)
def secure_api_app(request):
    options = {"swagger_ui": False}
    return build_app_from_fixture(
        "secure_api", request.param, options=options, auth_all_paths=True
    )


@pytest.fixture(scope="session", params=SPECS)
def unordered_definition_app(request):
    return build_app_from_fixture("unordered_definition", request.param)


@pytest.fixture(scope="session", params=SPECS)
def bad_operations_app(request):
    return build_app_from_fixture("bad_operations", request.param, resolver_error=501)


@pytest.fixture(scope="session", params=SPECS)
def method_view_app(request):
    return build_app_from_fixture(
        "method_view",
        request.param,
        resolver=MethodViewResolver("fakeapi.example_method_view"),
    )


@pytest.fixture(scope="session", params=METHOD_VIEW_RESOLVERS)
def method_view_resolver(request):
    return request.param
