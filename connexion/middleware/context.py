"""The ContextMiddleware creates a global context based the scope. It should be last in the
middleware stack, so it exposes the scope passed to the application"""
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.context import _context, _operation, _receive, _scope
from connexion.middleware.abstract import RoutedAPI, RoutedMiddleware
from connexion.operations import AbstractOperation


class ContextOperation:
    def __init__(
        self,
        next_app: ASGIApp,
        *,
        operation: AbstractOperation,
    ) -> None:
        self.next_app = next_app
        self.operation = operation

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        _context.set(scope.get("extensions", {}).get("connexion_context", {}))
        _operation.set(self.operation)
        _receive.set(receive)
        _scope.set(scope)
        await self.next_app(scope, receive, send)


class ContextAPI(RoutedAPI[ContextOperation]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_paths()

    def make_operation(self, operation: AbstractOperation) -> ContextOperation:
        return ContextOperation(self.next_app, operation=operation)


class ContextMiddleware(RoutedMiddleware[ContextAPI]):
    """Middleware to expose operation specific context to application."""

    api_cls = ContextAPI
