import pathlib
import typing as t
from contextvars import ContextVar

from starlette.routing import Router
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis import AbstractRoutingAPI
from connexion.exceptions import NotFoundProblem
from connexion.middleware import AppMiddleware
from connexion.resolver import Resolver

ROUTING_CONTEXT = 'connexion_routing'


_scope: ContextVar[dict] = ContextVar('SCOPE')


class RoutingMiddleware(AppMiddleware):

    def __init__(self, app: ASGIApp) -> None:
        """Middleware that resolves the Operation for an incoming request and attaches it to the
        scope.

        :param app: app to wrap in middleware.
        """
        self.app = app
        # Pass unknown routes to next app
        self.router = Router(default=RoutingOperation(None, self.app))

    def add_api(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
            **kwargs
    ) -> None:
        """Add an API to the router based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        api = RoutingAPI(specification, base_path=base_path, arguments=arguments,
                         next_app=self.app, **kwargs)
        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route request to matching operation, and attach it to the scope before calling the
        next app."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        _scope.set(scope.copy())

        # Needs to be set so starlette router throws exceptions instead of returning error responses
        scope['app'] = self
        try:
            await self.router(scope, receive, send)
        except ValueError:
            raise NotFoundProblem


class RoutingAPI(AbstractRoutingAPI):

    def __init__(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
            resolver: t.Optional[Resolver] = None,
            next_app: ASGIApp = None,
            resolver_error_handler: t.Optional[t.Callable] = None,
            debug: bool = False,
            **kwargs
    ) -> None:
        """API implementation on top of Starlette Router for Connexion middleware."""
        self.next_app = next_app
        self.router = Router(default=RoutingOperation(None, next_app))

        super().__init__(
            specification,
            base_path=base_path,
            arguments=arguments,
            resolver=resolver,
            resolver_error_handler=resolver_error_handler,
            debug=debug
        )

    def add_operation(self, path: str, method: str) -> None:
        operation_cls = self.specification.operation_cls
        operation = operation_cls.from_spec(self.specification, self, path, method, self.resolver)
        routing_operation = RoutingOperation(operation.operation_id, next_app=self.next_app)
        self._add_operation_internal(method, path, routing_operation)

    def _add_operation_internal(self, method: str, path: str, operation: 'RoutingOperation') -> None:
        self.router.add_route(path, operation, methods=[method])


class RoutingOperation:

    def __init__(self, operation_id: t.Optional[str], next_app: ASGIApp) -> None:
        self.operation_id = operation_id
        self.next_app = next_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Attach operation to scope and pass it to the next app"""
        original_scope = _scope.get()

        api_base_path = scope.get('root_path', '')[len(original_scope.get('root_path', '')):]

        extensions = original_scope.setdefault('extensions', {})
        connexion_routing = extensions.setdefault(ROUTING_CONTEXT, {})
        connexion_routing.update({
            'api_base_path': api_base_path,
            'operation_id': self.operation_id
        })
        await self.next_app(original_scope, receive, send)
