import logging

import pytest
from connexion.middleware import MiddlewarePosition
from connexion.options import SwaggerUIOptions
from starlette.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send

from conftest import OPENAPI3_SPEC, build_app_from_fixture


@pytest.fixture(scope="session")
def simple_app(spec, app_class):
    return build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, validate_responses=True
    )


@pytest.fixture(scope="session")
def simple_openapi_app(app_class):
    return build_app_from_fixture(
        "simple", app_class=app_class, spec_file=OPENAPI3_SPEC, validate_responses=True
    )


@pytest.fixture(scope="session")
def swagger_ui_app(app_class):
    return build_app_from_fixture(
        "simple",
        app_class=app_class,
        spec_file=OPENAPI3_SPEC,
        validate_responses=True,
        swagger_ui_options=SwaggerUIOptions(spec_path="/spec.json"),
    )


@pytest.fixture(scope="session")
def cors_openapi_app(app_class):
    app = build_app_from_fixture(
        "simple",
        app_class=app_class,
        spec_file=OPENAPI3_SPEC,
        validate_responses=True,
    )

    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["http://localhost"],
    )

    return app


@pytest.fixture(scope="session")
def reverse_proxied_app(spec, app_class):
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
                root_path = "/" + root_path.strip("/")
                scope["root_path"] = root_path
                scope["path"] = root_path + scope.get("path", "")
                scope["raw_path"] = root_path.encode() + scope.get("raw_path", "")

            scope["scheme"] = scope.get("scheme") or self.scheme
            scope["server"] = scope.get("server") or (self.server, None)

            return await self.app(scope, receive, send)

    app = build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, validate_responses=True
    )
    app.middleware = ReverseProxied(app.middleware, root_path="/reverse_proxied/")
    return app


@pytest.fixture(scope="session")
def snake_case_app(spec, app_class):
    return build_app_from_fixture(
        "snake_case",
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
        pythonic_params=True,
    )


@pytest.fixture(scope="session")
def invalid_resp_allowed_app(spec, app_class):
    return build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, validate_responses=False
    )


@pytest.fixture(scope="session")
def strict_app(spec, app_class):
    return build_app_from_fixture(
        "simple",
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
        strict_validation=True,
    )


@pytest.fixture(scope="session")
def problem_app(spec, app_class):
    return build_app_from_fixture(
        "problem", app_class=app_class, spec_file=spec, validate_responses=True
    )


@pytest.fixture(scope="session")
def schema_app(spec, app_class):
    return build_app_from_fixture(
        "different_schemas",
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
    )


@pytest.fixture(scope="session")
def secure_endpoint_app(spec, app_class):
    return build_app_from_fixture(
        "secure_endpoint",
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
    )


@pytest.fixture(scope="session")
def secure_endpoint_strict_app(spec, app_class):
    return build_app_from_fixture(
        "secure_endpoint",
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
        strict_validation=True,
    )


@pytest.fixture(scope="session")
def secure_api_app(spec, app_class):
    options = {"swagger_ui": False}
    return build_app_from_fixture(
        "secure_api",
        app_class=app_class,
        spec_file=spec,
        options=options,
        auth_all_paths=True,
    )


@pytest.fixture(scope="session")
def unordered_definition_app(spec, app_class):
    return build_app_from_fixture(
        "unordered_definition", app_class=app_class, spec_file=spec
    )


@pytest.fixture(scope="session")
def bad_operations_app(spec, app_class):
    return build_app_from_fixture(
        "bad_operations", app_class=app_class, spec_file=spec, resolver_error=501
    )
