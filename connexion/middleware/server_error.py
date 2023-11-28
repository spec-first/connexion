import logging

from starlette.middleware.errors import (
    ServerErrorMiddleware as StarletteServerErrorMiddleware,
)
from starlette.requests import Request as StarletteRequest
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import InternalServerError
from connexion.lifecycle import ConnexionResponse

logger = logging.getLogger(__name__)


class ServerErrorMiddleware(StarletteServerErrorMiddleware):
    """Subclass of starlette ServerErrorMiddleware to change handling of Unhandled Server
    exceptions to existing connexion behavior."""

    def __init__(self, next_app: ASGIApp):
        super().__init__(next_app)

    @staticmethod
    def error_response(_request: StarletteRequest, exc: Exception) -> ConnexionResponse:
        """Default handler for any unhandled Exception"""
        logger.error("%r", exc, exc_info=exc)
        return InternalServerError().to_problem()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await super().__call__(scope, receive, send)
