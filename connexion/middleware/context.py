"""The ContextMiddleware creates a global context based the scope. It should be last in the
middleware stack, so it exposes the scope passed to the application"""
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.context import _scope


class ContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        _scope.set(scope)
        await self.app(scope, receive, send)
