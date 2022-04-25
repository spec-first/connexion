import pytest
from connexion.middleware import ConnexionMiddleware
from starlette.datastructures import MutableHeaders

from conftest import SPECS, build_app_from_fixture


class TestMiddleware:
    """Middleware to check if operation is accessible on scope."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        operation_id = scope['extensions']['connexion_routing']['operation_id']

        async def patched_send(message):
            if message["type"] != "http.response.start":
                await send(message)
                return

            message.setdefault("headers", [])
            headers = MutableHeaders(scope=message)
            headers["operation_id"] = operation_id

            await send(message)

        await self.app(scope, receive, patched_send)


@pytest.fixture(scope="session", params=SPECS)
def middleware_app(request):
    middlewares = ConnexionMiddleware.default_middlewares + [TestMiddleware]
    return build_app_from_fixture('simple', request.param, middlewares=middlewares)


def test_routing_middleware(middleware_app):
    app_client = middleware_app.app.test_client()

    response = app_client.post("/v1.0/greeting/robbe")

    assert response.headers.get('operation_id') == 'fakeapi.hello.post_greeting', \
        response.status_code
