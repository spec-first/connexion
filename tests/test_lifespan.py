import contextlib
import sys
from unittest import mock

import pytest
from connexion import AsyncApp, ConnexionMiddleware


def test_lifespan_handler(app_class):
    m = mock.MagicMock()

    @contextlib.asynccontextmanager
    async def lifespan(app):
        m.startup()
        yield
        m.shutdown()

    app = AsyncApp(__name__, lifespan=lifespan)
    with app.test_client():
        m.startup.assert_called()
        m.shutdown.assert_not_called()
    m.shutdown.assert_called()


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="AsyncMock only available from 3.8."
)
async def test_lifespan():
    """Test that lifespan events are passed through if no handler is registered."""
    lifecycle_handler = mock.Mock()

    async def check_lifecycle(scope, receive, send):
        if scope["type"] == "lifespan":
            lifecycle_handler.handle()

    test_app = ConnexionMiddleware(check_lifecycle)
    await test_app({"type": "lifespan"}, mock.AsyncMock(), mock.AsyncMock())
    lifecycle_handler.handle.assert_called()
