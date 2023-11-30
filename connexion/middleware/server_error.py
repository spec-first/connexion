from starlette.middleware.errors import (
    ServerErrorMiddleware as StarletteServerErrorMiddleware,
)
from starlette.types import ASGIApp


class ServerErrorMiddleware(StarletteServerErrorMiddleware):
    """Subclass of starlette ServerErrorMiddleware to change handling of Unhandled Server
    exceptions to existing connexion behavior."""

    def __init__(self, next_app: ASGIApp):
        super().__init__(next_app)
