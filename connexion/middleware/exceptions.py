import logging

from starlette.exceptions import ExceptionMiddleware as StarletteExceptionMiddleware
from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import InternalServerError, ProblemException, problem

logger = logging.getLogger(__name__)


class ExceptionMiddleware(StarletteExceptionMiddleware):
    """Subclass of starlette ExceptionMiddleware to change handling of HTTP exceptions to
    existing connexion behavior."""

    def __init__(self, next_app: ASGIApp):
        super().__init__(next_app)
        self.add_exception_handler(ProblemException, self.problem_handler)
        self.add_exception_handler(Exception, self.common_error_handler)

    @staticmethod
    def problem_handler(_request: StarletteRequest, exc: ProblemException):
        logger.exception(exc)

        response = exc.to_problem()

        return Response(
            content=response.body,
            status_code=response.status_code,
            media_type=response.mimetype,
            headers=response.headers,
        )

    @staticmethod
    def http_exception(_request: StarletteRequest, exc: HTTPException) -> Response:
        logger.exception(exc)

        headers = exc.headers

        connexion_response = problem(
            title=exc.detail, detail=exc.detail, status=exc.status_code, headers=headers
        )

        return Response(
            content=connexion_response.body,
            status_code=connexion_response.status_code,
            media_type=connexion_response.mimetype,
            headers=connexion_response.headers,
        )

    @staticmethod
    def common_error_handler(_request: StarletteRequest, exc: Exception) -> Response:
        logger.exception(exc)

        response = InternalServerError().to_problem()

        return Response(
            content=response.body,
            status_code=response.status_code,
            media_type=response.mimetype,
            headers=response.headers,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Needs to be set so starlette router throws exceptions instead of returning error responses
        scope["app"] = "connexion"
        await super().__call__(scope, receive, send)
