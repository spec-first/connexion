import logging
import pathlib

import pytest
from connexion import App
from connexion.resolver import MethodResolver, MethodViewResolver
from starlette.types import Receive, Scope, Send
from werkzeug.test import Client

logging.basicConfig(level=logging.INFO)

TEST_FOLDER = pathlib.Path(__file__).parent
FIXTURES_FOLDER = TEST_FOLDER / "fixtures"
SPEC_FOLDER = TEST_FOLDER / "fakeapi"
OPENAPI2_SPEC = "swagger.yaml"
OPENAPI3_SPEC = "openapi.yaml"
SPECS = [OPENAPI2_SPEC, OPENAPI3_SPEC]
METHOD_VIEW_RESOLVERS = [MethodResolver, MethodViewResolver]


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


@pytest.fixture(scope="session", params=SPECS)
def spec(request):
    return request.param


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


@pytest.fixture(scope="session")
def simple_app(spec):
    return build_app_from_fixture("simple", validate_responses=True)


@pytest.fixture(scope="session")
def simple_openapi_app():
    return build_app_from_fixture("simple", OPENAPI3_SPEC, validate_responses=True)


@pytest.fixture(scope="session")
def reverse_proxied_app(spec):
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

    app = build_app_from_fixture("simple", spec, validate_responses=True)
    app.middleware = ReverseProxied(app.middleware, root_path="/reverse_proxied/")
    return app


@pytest.fixture(scope="session")
def snake_case_app(spec):
    return build_app_from_fixture(
        "snake_case", spec, validate_responses=True, pythonic_params=True
    )


@pytest.fixture(scope="session")
def invalid_resp_allowed_app(spec):
    return build_app_from_fixture("simple", spec, validate_responses=False)


@pytest.fixture(scope="session")
def strict_app(spec):
    return build_app_from_fixture(
        "simple", spec, validate_responses=True, strict_validation=True
    )


@pytest.fixture(scope="session")
def problem_app(spec):
    return build_app_from_fixture("problem", spec, validate_responses=True)


@pytest.fixture(scope="session")
def schema_app(spec):
    return build_app_from_fixture("different_schemas", spec, validate_responses=True)


@pytest.fixture(scope="session")
def secure_endpoint_app(spec):
    return build_app_from_fixture(
        "secure_endpoint",
        spec,
        validate_responses=True,
    )


@pytest.fixture(scope="session")
def secure_api_app(spec):
    options = {"swagger_ui": False}
    return build_app_from_fixture(
        "secure_api", spec, options=options, auth_all_paths=True
    )


@pytest.fixture(scope="session")
def unordered_definition_app(spec):
    return build_app_from_fixture("unordered_definition", spec)


@pytest.fixture(scope="session")
def bad_operations_app(spec):
    return build_app_from_fixture("bad_operations", spec, resolver_error=501)


@pytest.fixture(scope="session")
def method_view_app(spec):
    return build_app_from_fixture(
        "method_view",
        spec,
        resolver=MethodViewResolver("fakeapi.example_method_view"),
    )


@pytest.fixture(scope="session", params=METHOD_VIEW_RESOLVERS)
def method_view_resolver(request):
    return request.param
