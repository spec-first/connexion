import json

import werkzeug.exceptions
from starlette.exceptions import ExceptionMiddleware as StarletteExceptionMiddleware
from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from connexion.exceptions import ProblemException, problem


class ExceptionMiddleware(StarletteExceptionMiddleware):
    """Subclass of starlette ExceptionMiddleware to change handling of HTTP exceptions to
    existing connexion behavior."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_exception_handler(ProblemException, self.problem_handler)
        self.add_exception_handler(Exception, self.common_error_handler)

    def problem_handler(self, _request: StarletteRequest, exception: ProblemException):
        connexion_response = problem(
            status=exception.status,
            title=exception.title,
            detail=exception.detail,
            type=exception.type,
            instance=exception.instance,
            headers=exception.headers,
            ext=exception.ext,
        )

        return Response(
            content=json.dumps(connexion_response.body),
            status_code=connexion_response.status_code,
            media_type=connexion_response.mimetype,
            headers=connexion_response.headers,
        )

    def http_exception(
        self, _request: StarletteRequest, exc: HTTPException
    ) -> Response:
        headers = exc.headers

        connexion_response = problem(
            title=exc.detail, detail=exc.detail, status=exc.status_code, headers=headers
        )

        return Response(
            content=json.dumps(connexion_response.body),
            status_code=connexion_response.status_code,
            media_type=connexion_response.mimetype,
            headers=connexion_response.headers,
        )

    def common_error_handler(
        self, _request: StarletteRequest, exc: HTTPException
    ) -> Response:
        exception = werkzeug.exceptions.InternalServerError()

        response = problem(
            title=exception.name,
            detail=exception.description,
            status=exception.code,
        )

        return Response(
            content=json.dumps(response.body),
            status_code=response.status_code,
            media_type=response.mimetype,
            headers=response.headers,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Needs to be set so starlette router throws exceptions instead of returning error responses
        scope["app"] = self
        await super().__call__(scope, receive, send)
