from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from connexion.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from connexion.operations import AbstractOperation


class TestMiddleware(BaseHTTPMiddleware):
    """Middleware to check if operation is accessible on scope."""

    async def dispatch(self, request: StarletteRequest, operation: AbstractOperation,
                       call_next: RequestResponseEndpoint) -> StarletteResponse:
        response = await call_next(request)
        response.headers.update({'operation_id': operation.operation_id})
        return response
