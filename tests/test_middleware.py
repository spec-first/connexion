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


class RoutePathMiddleware:
    """Middleware to check if scope["route"].path is set for OTEL compatibility."""

    __test__ = False

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Read scope["route"].path which OTEL ASGI middleware uses for http.route
        route_obj = scope.get("route")
        route_path = route_obj.path if route_obj else ""

        async def patched_send(message):
            if message["type"] != "http.response.start":
                await send(message)
                return

            message.setdefault("headers", [])
            headers = MutableHeaders(scope=message)
            headers["x-route-path"] = route_path

            await send(message)

        await self.app(scope, receive, patched_send)


@pytest.fixture(scope="session")
def middleware_app(spec, app_class):
    middlewares = ConnexionMiddleware.default_middlewares + [TestMiddleware]
    return build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, middlewares=middlewares
    )


@pytest.fixture(scope="session")
def route_path_app(spec, app_class):
    middlewares = ConnexionMiddleware.default_middlewares + [RoutePathMiddleware]
    return build_app_from_fixture(
        "simple", app_class=app_class, spec_file=spec, middlewares=middlewares
    )


def test_routing_middleware(middleware_app):
    app_client = middleware_app.test_client()

    response = app_client.post("/v1.0/greeting/robbe")

    assert (
        response.headers.get("operation_id") == "fakeapi.hello.post_greeting"
    ), response.status_code


def test_route_path_for_otel(route_path_app):
    """Test that scope['route'].path is set for OpenTelemetry instrumentation.

    OTEL ASGI middleware reads scope["route"].path to populate the http.route
    attribute on spans and metrics, which is required for proper transaction
    naming in APM tools like NewRelic.
    """
    app_client = route_path_app.test_client()

    response = app_client.post("/v1.0/greeting/robbe")

    # The route path should be the OpenAPI path template with base path
    assert (  # nosec B101
        response.headers.get("x-route-path") == "/v1.0/greeting/{name}"
    ), f"Expected /v1.0/greeting/{{name}}, got {response.headers.get('x-route-path')}"


def test_route_path_with_multiple_params(route_path_app):
    """Test route path with multiple path parameters."""
    app_client = route_path_app.test_client()

    response = app_client.post("/v1.0/greeting/robbe/extra/path")

    # Path with remainder parameter
    assert (  # nosec B101
        response.headers.get("x-route-path") == "/v1.0/greeting/{name}/{remainder}"
    ), f"Expected /v1.0/greeting/{{name}}/{{remainder}}, got {response.headers.get('x-route-path')}"


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


class TestRoutingHooks:
    """Tests for the after_routing_resolution hook mechanism."""

    def test_hook_receives_route_info(self, spec, app_class):
        """Test that registered hooks receive route path and operation_id."""
        from connexion.middleware.routing import RoutingOperation

        # Clear any existing hooks from other tests
        RoutingOperation.clear_routing_hooks()

        captured = {}

        def capture_route_info(route_path, operation_id, scope):
            captured["route_path"] = route_path
            captured["operation_id"] = operation_id
            captured["method"] = scope.get("method")

        RoutingOperation.after_routing_resolution(capture_route_info)

        try:
            app = build_app_from_fixture("simple", app_class=app_class, spec_file=spec)
            app_client = app.test_client()
            app_client.post("/v1.0/greeting/robbe")

            assert captured["route_path"] == "/v1.0/greeting/{name}"  # nosec B101
            assert (
                captured["operation_id"] == "fakeapi.hello.post_greeting"
            )  # nosec B101
            assert captured["method"] == "POST"  # nosec B101
        finally:
            RoutingOperation.clear_routing_hooks()

    def test_multiple_hooks(self, spec, app_class):
        """Test that multiple hooks are all invoked."""
        from connexion.middleware.routing import RoutingOperation

        RoutingOperation.clear_routing_hooks()

        call_count = {"first": 0, "second": 0}

        def first_hook(route_path, operation_id, scope):
            call_count["first"] += 1

        def second_hook(route_path, operation_id, scope):
            call_count["second"] += 1

        RoutingOperation.after_routing_resolution(first_hook)
        RoutingOperation.after_routing_resolution(second_hook)

        try:
            app = build_app_from_fixture("simple", app_class=app_class, spec_file=spec)
            app_client = app.test_client()
            app_client.post("/v1.0/greeting/robbe")

            assert call_count["first"] == 1  # nosec B101
            assert call_count["second"] == 1  # nosec B101
        finally:
            RoutingOperation.clear_routing_hooks()

    def test_hook_error_does_not_break_request(self, spec, app_class):
        """Test that hook errors don't break request processing."""
        from connexion.middleware.routing import RoutingOperation

        RoutingOperation.clear_routing_hooks()

        def failing_hook(route_path, operation_id, scope):
            raise RuntimeError("Intentional error")

        RoutingOperation.after_routing_resolution(failing_hook)

        try:
            app = build_app_from_fixture("simple", app_class=app_class, spec_file=spec)
            app_client = app.test_client()
            # Request should still succeed despite hook error
            response = app_client.post("/v1.0/greeting/robbe")
            assert response.status_code == 200  # nosec B101
        finally:
            RoutingOperation.clear_routing_hooks()
