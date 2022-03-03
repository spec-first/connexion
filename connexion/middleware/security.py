from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from connexion.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from connexion.operations import AbstractOperation


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to check security."""

    async def dispatch(self, request: StarletteRequest, operation: AbstractOperation,
                       call_next: RequestResponseEndpoint) -> StarletteResponse:
        # Shortcut for now, should be implemented cleanly
        await operation.security_decorator(lambda _: None)(request)
        response = await call_next(request)
        return response
