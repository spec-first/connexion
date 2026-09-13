import logging
import typing as t

from starlette.middleware.errors import (
    ServerErrorMiddleware as StarletteServerErrorMiddleware,
)
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp

from connexion.exceptions import InternalServerError
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware.exceptions import connexion_wrapper
from connexion.types import MaybeAwaitable

logger = logging.getLogger(__name__)


class ServerErrorMiddleware(StarletteServerErrorMiddleware):
    """Subclass of starlette ServerErrorMiddleware to change handling of Unhandled Server
    exceptions to existing connexion behavior."""

    def __init__(
        self,
        next_app: ASGIApp,
        handler: t.Optional[
            t.Callable[[ConnexionRequest, Exception], MaybeAwaitable[ConnexionResponse]]
        ] = None,
    ):
        handler = connexion_wrapper(handler) if handler else None
        super().__init__(next_app, handler=handler)

    @staticmethod
    def error_response(_request: StarletteRequest, exc: Exception) -> StarletteResponse:
        """Default handler for any unhandled Exception"""
        logger.error("%r", exc, exc_info=exc)
        problem_response = InternalServerError().to_problem()
        return StarletteResponse(
            content=problem_response.body,
            status_code=problem_response.status_code,
            media_type=problem_response.mimetype,
            headers=problem_response.headers,
        )
