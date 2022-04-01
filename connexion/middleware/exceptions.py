import json

from starlette.exceptions import \
    ExceptionMiddleware as StarletteExceptionMiddleware
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from connexion.exceptions import problem


class ExceptionMiddleware(StarletteExceptionMiddleware):
    """Subclass of starlette ExceptionMiddleware to change handling of HTTP exceptions to
    existing connexion behavior."""

    def http_exception(self, request: Request, exc: HTTPException) -> Response:
        try:
            headers = exc.headers
        except AttributeError:
            # Starlette < 0.19
            headers = {}

        connexion_response = problem(title=exc.detail,
                                     detail=exc.detail,
                                     status=exc.status_code,
                                     headers=headers)

        return Response(
            content=json.dumps(connexion_response.body),
            status_code=connexion_response.status_code,
            media_type=connexion_response.mimetype,
            headers=connexion_response.headers
        )
