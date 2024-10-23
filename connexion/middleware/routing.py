import typing as t
from contextvars import ContextVar

import starlette.convertors
from starlette.routing import Router
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.frameworks import starlette as starlette_utils
from connexion.middleware.abstract import (
    ROUTING_CONTEXT,
    AbstractRoutingAPI,
    SpecMiddleware,
)
from connexion.operations import AbstractOperation
from connexion.resolver import Resolver
from connexion.spec import Specification

_scope: ContextVar[dict] = ContextVar("SCOPE")


class RoutingOperation:
    def __init__(self, operation_id: t.Optional[str], next_app: ASGIApp) -> None:
        self.operation_id = operation_id
        self.next_app = next_app

    @classmethod
    def from_operation(cls, operation: AbstractOperation, next_app: ASGIApp):
        return cls(operation.operation_id, next_app)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Attach operation to scope and pass it to the next app"""
        original_scope = _scope.get()
        # Pass resolved path params along
        original_scope.setdefault("path_params", {}).update(
            scope.get("path_params", {})
        )

        def get_root_path(scope: Scope) -> str:
            return scope.get("route_root_path", scope.get("root_path", ""))

        api_base_path = get_root_path(scope)[len(get_root_path(original_scope)) :]

        extensions = original_scope.setdefault("extensions", {})
        connexion_routing = extensions.setdefault(ROUTING_CONTEXT, {})
        connexion_routing.update(
            {"api_base_path": api_base_path, "operation_id": self.operation_id}
        )
        await self.next_app(original_scope, receive, send)


class RoutingAPI(AbstractRoutingAPI):
    def __init__(
        self,
        specification: Specification,
        *,
        next_app: ASGIApp,
        base_path: t.Optional[str] = None,
        arguments: t.Optional[dict] = None,
        resolver: t.Optional[Resolver] = None,
        resolver_error_handler: t.Optional[t.Callable] = None,
        debug: bool = False,
        **kwargs,
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
            debug=debug,
            **kwargs,
        )

    def make_operation(self, operation: AbstractOperation) -> RoutingOperation:
        return RoutingOperation.from_operation(operation, next_app=self.next_app)

    @staticmethod
    def _framework_path_and_name(
        operation: AbstractOperation, path: str
    ) -> t.Tuple[str, str]:
        types = operation.get_path_parameter_types()
        starlette_path = starlette_utils.starlettify_path(path, types)
        return starlette_path, starlette_path

    def _add_operation_internal(
        self,
        method: str,
        path: str,
        operation: RoutingOperation,
        name: t.Optional[str] = None,
    ) -> None:
        self.router.add_route(path, operation, methods=[method])


class RoutingMiddleware(SpecMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        """Middleware that resolves the Operation for an incoming request and attaches it to the
        scope.

        :param app: app to wrap in middleware.
        """
        self.app = app
        # Pass unknown routes to next app
        self.router = Router(default=RoutingOperation(None, self.app))
        starlette.convertors.register_url_convertor(
            "float", starlette_utils.FloatConverter()
        )
        starlette.convertors.register_url_convertor(
            "int", starlette_utils.IntegerConverter()
        )

    def add_api(
        self,
        specification: Specification,
        base_path: t.Optional[str] = None,
        arguments: t.Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Add an API to the router based on a OpenAPI spec.

        :param specification: OpenAPI spec.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        api = RoutingAPI(
            specification,
            base_path=base_path,
            arguments=arguments,
            next_app=self.app,
            **kwargs,
        )

        # If an API with the same base_path was already registered, chain the new API as its
        # default. This way, if no matching route is found on the first API, the request is
        # forwarded to the new API.
        for route in self.router.routes:
            if (
                isinstance(route, starlette.routing.Mount)
                and route.path == api.base_path
            ):
                route.app.default = api.router

        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route request to matching operation, and attach it to the scope before calling the
        next app."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        _scope.set(scope.copy())  # type: ignore

        await self.router(scope, receive, send)
