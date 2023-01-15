"""
This module defines a native connexion asynchronous application.
"""

import logging
import typing as t

from starlette.responses import Response as StarletteResponse
from starlette.routing import Router
from starlette.types import Receive, Scope, Send

from connexion.apps.abstract import AbstractApp
from connexion.decorators import StarletteDecorator
from connexion.middleware.abstract import (
    AbstractRoutingAPI,
    RoutedAPI,
    RoutedMiddleware,
)
from connexion.operations import AbstractOperation
from connexion.uri_parsing import AbstractURIParser

logger = logging.getLogger("Connexion.app")


class AsyncOperation:
    def __init__(
        self,
        operation: AbstractOperation,
        fn: t.Callable,
        uri_parser: AbstractURIParser,
        api: AbstractRoutingAPI,
        operation_id: str,
        pythonic_params: bool,
    ) -> None:
        self._operation = operation
        self._fn = fn
        self.uri_parser = uri_parser
        self.api = api
        self.operation_id = operation_id
        self.pythonic_params = pythonic_params

    @classmethod
    def from_operation(
        cls, operation: AbstractOperation, pythonic_params: bool
    ) -> "AsyncOperation":
        return cls(
            operation,
            fn=operation.function,
            uri_parser=operation.uri_parser_class,
            api=operation.api,
            operation_id=operation.operation_id,
            pythonic_params=pythonic_params,
        )

    @property
    def fn(self) -> t.Callable:
        decorator = StarletteDecorator(
            pythonic_params=self.pythonic_params,
            jsonifier=self.api.jsonifier,
        )
        return decorator(self._fn)

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> StarletteResponse:
        return await self.fn(scope=scope, receive=receive, send=send)


class AsyncApi(RoutedAPI[AsyncOperation]):
    def __init__(self, *args, pythonic_params: bool, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pythonic_params = pythonic_params
        self.router = Router()
        self.add_paths()

    def make_operation(self, operation: AbstractOperation) -> AsyncOperation:
        return AsyncOperation.from_operation(operation, self.pythonic_params)


class AsyncMiddlewareApp(RoutedMiddleware[AsyncApi]):
    def __init__(self) -> None:
        self.apis: t.Dict[str, AsyncApi] = {}
        self.operations: t.Dict[str, AsyncOperation] = {}
        self.router = Router()
        super().__init__(self.router)

    def add_api(self, *args, **kwargs):
        api = AsyncApi(*args, **kwargs)
        self.apis[api.base_path] = api
        self.router.mount(api.base_path, api.router)
        return api

    def add_url_rule(
        self,
        rule,
        endpoint: str = None,
        view_func: t.Callable = None,
        methods: t.List[str] = None,
        **options
    ):
        self.router.add_route(rule, endpoint=view_func, name=endpoint, methods=methods)


class AsyncApp(AbstractApp):
    """Connexion Application based on ConnexionMiddleware wrapping a async Connexion application
    based on starlette tools."""

    middleware_app = AsyncMiddlewareApp()

    def add_url_rule(
        self, rule, endpoint: str = None, view_func: t.Callable = None, **options
    ):
        self.middleware_app.add_url_rule(
            rule, endpoint=endpoint, view_func=view_func, **options
        )

    def add_error_handler(
        self, code_or_exception: t.Union[int, t.Type[Exception]], function: t.Callable
    ) -> None:
        """TODO: implement"""

    def test_client(self, **kwargs):
        """TODO: implement"""
