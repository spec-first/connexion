import logging

from starlette.middleware.errors import (
    ServerErrorMiddleware as StarletteServerErrorMiddleware,
)
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class ServerErrorMiddleware(StarletteServerErrorMiddleware):
    """Subclass of starlette ServerErrorMiddleware to change handling of Unhandled Server
    exceptions to existing connexion behavior."""

    def __init__(self, next_app: ASGIApp):
        super().__init__(next_app)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await super().__call__(scope, receive, send)
