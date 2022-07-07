"""
This module defines a native connexion asynchronous application.
"""

import asyncio
import logging
import os
import pathlib
import sys
import typing as t

from starlette.routing import Router
from starlette.types import Receive, Scope, Send

from .abstract import AbstractApp
from connexion.apis.abstract import AbstractRoutingAPI

from connexion.decorators.uri_parsing import AbstractURIParser
from connexion.exceptions import MissingMiddleware, ProblemException
from connexion.lifecycle import MiddlewareRequest
from connexion.middleware.main import ConnexionMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from ..operations import AbstractOperation

logger = logging.getLogger("Connexion.app")


class AsyncAsgiApp:
    def __init__(self, *args, base_path="", **kwargs):
        self.apis: t.Dict[str, AsyncApi] = {}
        self.operations: t.Dict[str, AsyncOperation] = {}
        self.router = Router()
        self.base_path = base_path
        super(AsyncAsgiApp, self).__init__(*args, **kwargs)

    def add_api(self, specification: t.Union[pathlib.Path, str, dict], **kwargs):
        api = super(AsyncAsgiApp, self).add_api(specification, **kwargs)
        self.apis[api.base_path] = api
        return api

    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        self.router.add_route(path=rule, endpoint=view_func, name=endpoint, **options)

    def route(self, rule, **options):
        self.router.route(rule, **options)

    async def asgi_app(self, scope: Scope, receive: Receive, send: Send) -> None:
        """The actual ASGI application. This is not implemented in
        :meth:`__call__` so that middlewares can be applied without
        losing a reference to the app object.
        """
        try:
            connexion_context = scope["extensions"][ROUTING_CONTEXT]
        except KeyError:
            raise MissingMiddleware(
                "Could not find routing information in scope. Please make sure "
                "you have a routing middleware registered upstream. "
            )

        api_base_path = connexion_context.get("api_base_path")
        if api_base_path and not api_base_path == self.base_path:
            api = self.apis[api_base_path]
            await api(scope, receive, send)

        else:
            operation_id = connexion_context.get("operation_id")
            try:
                operation = self.operations[operation_id]
            except KeyError as e:
                if operation_id is None:
                    # Check if route was manually registered
                    await self.router(scope, receive, send)  # TODO: add router on API?
                else:
                    raise MissingAsyncOperation(
                        "Encountered unknown operation_id."
                    ) from e
            else:
                response = await operation(scope, receive, send)
                while asyncio.iscoroutine(response):
                    response = await response
                await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.asgi_app(scope, receive, send)


class AsyncApp(AsyncAsgiApp, AbstractApp):
    def __init__(self, *args, **kwargs) -> None:
        super(AsyncApp, self).__init__(*args, api_cls=AsyncApi, **kwargs)

    def _apply_middleware(self, middlewares):
        middleware = ConnexionMiddleware(self.asgi_app, middlewares=middlewares)
        self.asgi_app = middleware
        return middleware

    def get_root_path(self):
        # Module already imported and has a file attribute.  Use that first.
        mod = sys.modules.get(self.import_name)
        if mod is not None and hasattr(mod, "__file__"):
            return os.path.dirname(os.path.abspath(mod.__file__))

    def set_errors_handlers(self):
        pass


class AsyncApi(AsyncAsgiApp, AbstractRoutingAPI):
    def __init__(self, *args, **kwargs) -> None:
        super(AsyncApi, self).__init__(*args, **kwargs)
        self.add_paths()

    def add_operation(self, path: str, method: str) -> None:
        operation_cls = self.specification.operation_cls
        operation = operation_cls.from_spec(
            self.specification, self, path, method, self.resolver
        )
        async_operation = AsyncOperation.from_operation(operation)
        self._add_operation_internal(method, path, async_operation)

    def _add_operation_internal(
        self, method: str, path: str, operation: AbstractOperation
    ) -> None:
        self.operations[operation.operation_id] = operation


class AsyncOperation:
    def __init__(
        self,
        fn: t.Union[t.Callable, t.Awaitable],
        uri_parser: AbstractURIParser,
        operation_id: str = None,
    ) -> None:
        self.fn = fn
        self.uri_parser = uri_parser
        self.operation_id = operation_id

    @classmethod
    def from_operation(cls, operation: AbstractOperation) -> "AsyncOperation":
        return cls(
            operation.function, operation._uri_parsing_decorator, operation.operation_id
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = MiddlewareRequest(scope, receive, uri_parser=self.uri_parser)
        if asyncio.iscoroutinefunction(self.fn):
            return await self.fn(request)
        else:
            return self.fn(request)


class MissingAsyncOperation(ProblemException):
    def __init__(self, *args, **kwargs) -> None:
        super(MissingAsyncOperation, self).__init__(500, *args, **kwargs)
