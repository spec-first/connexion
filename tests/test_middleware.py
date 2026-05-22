import typing as t
from unittest.mock import Mock

import pytest
from connexion import FlaskApp
from connexion.middleware import ConnexionMiddleware, MiddlewarePosition
from connexion.middleware.swagger_ui import SwaggerUIMiddleware
from connexion.types import Environ, ResponseStream, StartResponse, WSGIApp
from starlette.datastructures import MutableHeaders

from conftest import build_app_from_fixture


class TestMiddleware:
    """Middleware to check if operation is accessible on scope."""

    __test__ = False

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        operation_id = scope["extensions"]["connexion_routing"]["operation_id"]

        async def patched_send(message):
            if message["type"] != "http.response.start":
                await send(message)
                return

            message.setdefault("headers", [])
            headers = MutableHeaders(scope=message)
            headers["operation_id"] = operation_id

            await send(message)

        await self.app(scope, receive, patched_send)


@pytest.fixture(scope="session")
def middleware_app(spec, app_class):
    middlewares = ConnexionMiddleware.default_middlewares + [TestMiddleware]
    return build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, middlewares=middlewares
    )


def test_routing_middleware(middleware_app):
    app_client = middleware_app.test_client()

    response = app_client.post("/v1.0/greeting/robbe")

    assert (
        response.headers.get("operation_id") == "fakeapi.hello.post_greeting"
    ), response.status_code


def test_add_middleware(spec, app_class):
    """Test adding middleware via the `add_middleware` method."""
    app = build_app_from_fixture("simple", app_class=app_class, spec_file=spec)
    app.add_middleware(TestMiddleware)

    app_client = app.test_client()
    response = app_client.post("/v1.0/greeting/robbe")

    assert (
        response.headers.get("operation_id") == "fakeapi.hello.post_greeting"
    ), response.status_code


def test_position(spec, app_class):
    """Test adding middleware via the `add_middleware` method."""
    middlewares = [
        middleware
        for middleware in ConnexionMiddleware.default_middlewares
        if middleware != SwaggerUIMiddleware
    ]
    app = build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, middlewares=middlewares
    )

    with pytest.raises(ValueError) as exc_info:
        app.add_middleware(TestMiddleware, position=MiddlewarePosition.BEFORE_SWAGGER)

    assert (
        exc_info.value.args[0]
        == f"Could not insert middleware at position BEFORE_SWAGGER. "
        f"Please make sure you have a {SwaggerUIMiddleware} in your stack."
    )


def test_add_wsgi_middleware(spec):
    app: FlaskApp = build_app_from_fixture("simple", app_class=FlaskApp, spec_file=spec)

    class WSGIMiddleware:
        def __init__(self, app_: WSGIApp, mock_counter):
            self.next_app = app_
            self.mock_counter = mock_counter

        def __call__(
            self, environ: Environ, start_response: StartResponse
        ) -> ResponseStream:
            self.mock_counter()
            return self.next_app(environ, start_response)

    mock = Mock()
    app.add_wsgi_middleware(WSGIMiddleware, mock_counter=mock)

    app_client = app.test_client()
    app_client.post("/v1.0/greeting/robbe")

    mock.assert_called_once()


def test_flask_wsgi_workers_default():
    """When wsgi_workers is not set, FlaskApp falls back to a2wsgi's default (10)."""
    app = FlaskApp(__name__)
    # a2wsgi's WSGIMiddleware exposes the ThreadPoolExecutor via .executor;
    # its _max_workers reflects the requested pool size.
    assert app._middleware_app.asgi_app.executor._max_workers == 10


def test_flask_wsgi_workers_configurable():
    """FlaskApp(wsgi_workers=N) sizes the WSGI ThreadPoolExecutor to N.

    Regression test for https://github.com/spec-first/connexion/issues/1979
    where the WSGI worker count was hard-coded to a2wsgi's default of 10
    and could only be changed by monkey-patching.
    """
    app = FlaskApp(__name__, wsgi_workers=42)
    assert app._middleware_app.asgi_app.executor._max_workers == 42
