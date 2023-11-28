import asyncio
import functools
import logging
import typing as t

from starlette.concurrency import run_in_threadpool
from starlette.middleware.errors import (
    ServerErrorMiddleware as StarletteServerErrorMiddleware,
)
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import InternalServerError
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.types import MaybeAwaitable

logger = logging.getLogger(__name__)


def connexion_wrapper(
    handler: t.Callable[
        [ConnexionRequest, Exception], MaybeAwaitable[ConnexionResponse]
    ]
) -> t.Callable[[StarletteRequest, Exception], t.Awaitable[StarletteResponse]]:
    """Wrapper that translates Starlette requests to Connexion requests before passing
    them to the error handler, and translates the returned Connexion responses to
    Starlette responses."""

    @functools.wraps(handler)
    async def wrapper(request: StarletteRequest, exc: Exception) -> StarletteResponse:
        request = ConnexionRequest.from_starlette_request(request)

        if asyncio.iscoroutinefunction(handler):
            response = await handler(request, exc)  # type: ignore
        else:
            response = await run_in_threadpool(handler, request, exc)

        while asyncio.iscoroutine(response):
            response = await response

        return StarletteResponse(
            content=response.body,
            status_code=response.status_code,
            media_type=response.mimetype,
            headers=response.headers,
        )

    return wrapper


class ServerErrorMiddleware(StarletteServerErrorMiddleware):
    """Subclass of starlette ServerErrorMiddleware to change handling of Unhandled Server
    exceptions to existing connexion behavior."""

    def __init__(self, next_app: ASGIApp):
        super().__init__(next_app)

    @staticmethod
    def error_response(
        _request: StarletteRequest, exc: Exception
    ) -> ConnexionResponse:
        """Default handler for any unhandled Exception"""
        logger.error("%r", exc, exc_info=exc)
        return InternalServerError().to_problem()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await super().__call__(scope, receive, send)
