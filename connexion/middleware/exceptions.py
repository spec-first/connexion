import asyncio
import logging
import typing as t

import werkzeug.exceptions
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware.exceptions import (
    ExceptionMiddleware as StarletteExceptionMiddleware,
)
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import InternalServerError, ProblemException, problem
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

    async def wrapper(request: StarletteRequest, exc: Exception) -> StarletteResponse:
        request = ConnexionRequest.from_starlette_request(request)

        if asyncio.iscoroutinefunction(handler):
            response = await handler(request, exc)  # type: ignore
        else:
            response = await run_in_threadpool(handler, request, exc)

        return StarletteResponse(
            content=response.body,
            status_code=response.status_code,
            media_type=response.mimetype,
            headers=response.headers,
        )

    return wrapper


class ExceptionMiddleware(StarletteExceptionMiddleware):
    """Subclass of starlette ExceptionMiddleware to change handling of HTTP exceptions to
    existing connexion behavior."""

    def __init__(self, next_app: ASGIApp):
        super().__init__(next_app)
        self.add_exception_handler(ProblemException, self.problem_handler)  # type: ignore
        self.add_exception_handler(
            werkzeug.exceptions.HTTPException, self.flask_error_handler
        )
        self.add_exception_handler(Exception, self.common_error_handler)

    def add_exception_handler(
        self,
        exc_class_or_status_code: t.Union[int, t.Type[Exception]],
        handler: t.Callable[[ConnexionRequest, Exception], StarletteResponse],
    ) -> None:
        super().add_exception_handler(
            exc_class_or_status_code, handler=connexion_wrapper(handler)
        )

    @staticmethod
    def problem_handler(_request: ConnexionRequest, exc: ProblemException):
        """Default handler for Connexion ProblemExceptions"""
        logger.error("%r", exc)
        return exc.to_problem()

    @staticmethod
    @connexion_wrapper
    def http_exception(
        _request: StarletteRequest, exc: HTTPException, **kwargs
    ) -> StarletteResponse:
        """Default handler for Starlette HTTPException"""
        logger.error("%r", exc)
        return problem(
            title=exc.detail,
            detail=exc.detail,
            status=exc.status_code,
            headers=exc.headers,
        )

    @staticmethod
    def common_error_handler(
        _request: StarletteRequest, exc: Exception
    ) -> ConnexionResponse:
        """Default handler for any unhandled Exception"""
        logger.error("%r", exc, exc_info=exc)
        return InternalServerError().to_problem()

    def flask_error_handler(
        self, request: StarletteRequest, exc: werkzeug.exceptions.HTTPException
    ) -> ConnexionResponse:
        """Default handler for Flask / werkzeug HTTPException"""
        # If a handler is registered for the received status_code, call it instead.
        # This is only done automatically for Starlette HTTPExceptions
        if handler := self._status_handlers.get(exc.code):
            starlette_exception = HTTPException(exc.code, detail=exc.description)
            return handler(request, starlette_exception)

        return problem(
            title=exc.name,
            detail=exc.description,
            status=exc.code,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Needs to be set so starlette router throws exceptions instead of returning error responses
        scope["app"] = "connexion"
        await super().__call__(scope, receive, send)
