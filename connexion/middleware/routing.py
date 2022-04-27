import pathlib
import typing as t
from contextlib import contextmanager
from contextvars import ContextVar

from starlette.requests import Request as StarletteRequest
from starlette.routing import Router
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis import AbstractMinimalAPI
from connexion.exceptions import NotFoundProblem
from connexion.middleware import AppMiddleware
from connexion.operations import AbstractOperation, make_operation
from connexion.resolver import Resolver

ROUTING_CONTEXT = 'connexion_routing'


_scope_receive_send: ContextVar[tuple] = ContextVar('SCOPE_RECEIVE_SEND')


class MiddlewareResolver(Resolver):

    def __init__(self, call_next: t.Callable) -> None:
        """Resolver that resolves each operation to the provided call_next function."""
        super().__init__()
        self.call_next = call_next

    def resolve_function_from_operation_id(self, operation_id: str) -> t.Callable:
        return self.call_next


class RoutingMiddleware(AppMiddleware):

    def __init__(self, app: ASGIApp) -> None:
        """Middleware that resolves the Operation for an incoming request and attaches it to the
        scope.

        :param app: app to wrap in middleware.
        """
        self.app = app
        # Pass unknown routes to next app
        self.router = Router(default=self.default_fn)

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
        kwargs.pop("resolver", None)
        resolver = MiddlewareResolver(self.create_call_next())
        api = MiddlewareAPI(specification, base_path=base_path, arguments=arguments,
                            resolver=resolver, default=self.default_fn, **kwargs)
        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route request to matching operation, and attach it to the scope before calling the
        next app."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        _scope_receive_send.set((scope.copy(), receive, send))

        # Needs to be set so starlette router throws exceptions instead of returning error responses
        scope['app'] = self
        try:
            await self.router(scope, receive, send)
        except ValueError:
            raise NotFoundProblem

    async def default_fn(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Callback to call next app as default when no matching route is found."""
        original_scope, *_ = _scope_receive_send.get()

        api_base_path = scope.get('root_path', '')[len(original_scope.get('root_path', '')):]

        extensions = original_scope.setdefault('extensions', {})
        connexion_routing = extensions.setdefault(ROUTING_CONTEXT, {})
        connexion_routing.update({
            'api_base_path': api_base_path
        })
        await self.app(original_scope, receive, send)

    def create_call_next(self):

        async def call_next(
                operation: AbstractOperation,
                request: StarletteRequest = None
        ) -> None:
            """Attach operation to scope and pass it to the next app"""
            scope, receive, send = _scope_receive_send.get()

            api_base_path = request.scope.get('root_path', '')[len(scope.get('root_path', '')):]

            extensions = scope.setdefault('extensions', {})
            connexion_routing = extensions.setdefault(ROUTING_CONTEXT, {})
            connexion_routing.update({
                'api_base_path': api_base_path,
                'operation_id': operation.operation_id
            })
            return await self.app(scope, receive, send)

        return call_next


class MiddlewareAPI(AbstractMinimalAPI):

    def __init__(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
            resolver: t.Optional[Resolver] = None,
            default: ASGIApp = None,
            resolver_error_handler: t.Optional[t.Callable] = None,
            debug: bool = False,
            **kwargs
    ) -> None:
        """API implementation on top of Starlette Router for Connexion middleware."""
        self.router = Router(default=default)

        super().__init__(
            specification,
            base_path=base_path,
            arguments=arguments,
            resolver=resolver,
            resolver_error_handler=resolver_error_handler,
            debug=debug
        )

    def add_operation(self, path: str, method: str) -> None:
        operation = make_operation(
            self.specification,
            self,
            path,
            method,
            self.resolver
        )

        @contextmanager
        def patch_operation_function():
            """Patch the operation function so no decorators are set in the middleware. This
            should be cleaned up by separating the APIs and Operations between the App and
            middleware"""
            original_operation_function = AbstractOperation.function
            AbstractOperation.function = operation._resolution.function
            try:
                yield
            finally:
                AbstractOperation.function = original_operation_function

        with patch_operation_function():
            self._add_operation_internal(method, path, operation)

    def _add_operation_internal(self, method: str, path: str, operation: AbstractOperation) -> None:
        self.router.add_route(path, operation.function, methods=[method])
