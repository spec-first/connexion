import sys
from unittest import mock

import pytest
from connexion.middleware import ConnexionMiddleware
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


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="AsyncMock only available from 3.8."
)
async def test_lifecycle():
    """Test that lifecycle events are passed correctly."""
    lifecycle_handler = mock.Mock()

    async def check_lifecycle(scope, receive, send):
        if scope["type"] == "lifecycle":
            lifecycle_handler.handle()

    test_app = ConnexionMiddleware(check_lifecycle)
    await test_app({"type": "lifecycle"}, mock.AsyncMock, mock.AsyncMock)
    lifecycle_handler.handle.assert_called()
