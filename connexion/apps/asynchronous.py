"""
This module defines a native connexion asynchronous application.
"""

import logging
import pathlib
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
from connexion.resolver import Resolver
from connexion.uri_parsing import AbstractURIParser

logger = logging.getLogger(__name__)


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
        **options,
    ):
        self.router.add_route(rule, endpoint=view_func, name=endpoint, methods=methods)


class AsyncApp(AbstractApp):
    """Connexion Application based on ConnexionMiddleware wrapping a async Connexion application
    based on starlette tools."""

    def __init__(
        self,
        import_name: str,
        *,
        specification_dir: t.Union[pathlib.Path, str] = "",
        middlewares: t.Optional[list] = None,
        arguments: t.Optional[dict] = None,
        auth_all_paths: t.Optional[bool] = None,
        pythonic_params: t.Optional[bool] = None,
        resolver: t.Optional[t.Union[Resolver, t.Callable]] = None,
        resolver_error: t.Optional[int] = None,
        strict_validation: t.Optional[bool] = None,
        swagger_ui_options: t.Optional[dict] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
        validate_responses: t.Optional[bool] = None,
        validator_map: t.Optional[dict] = None,
    ) -> None:
        """
        :param import_name: The name of the package or module that this object belongs to. If you
            are using a single module, __name__ is always the correct value. If you however are
            using a package, it’s usually recommended to hardcode the name of your package there.
        :param specification_dir: The directory holding the specification(s). The provided path
            should either be absolute or relative to the root path of the application. Defaults to
            the root path.
        :param middlewares: The list of middlewares to wrap around the application. Defaults to
            :obj:`middleware.main.ConnexionmMiddleware.default_middlewares`
        :param arguments: Arguments to substitute the specification using Jinja.
        :param auth_all_paths: whether to authenticate not paths not defined in the specification.
            Defaults to False.
        :param pythonic_params: When True, CamelCase parameters are converted to snake_case and an
            underscore is appended to any shadowed built-ins. Defaults to False.
        :param resolver: Callable that maps operationId to a function or instance of
            :class:`resolver.Resolver`.
        :param resolver_error: Error code to return for operations for which the operationId could
            not be resolved. If no error code is provided, the application will fail when trying to
            start.
        :param strict_validation: When True, extra form or query parameters not defined in the
            specification result in a validation error. Defaults to False.
        :param swagger_ui_options: A :class:`options.ConnexionOptions` instance with configuration
            options for the swagger ui.
        :param uri_parser_class: Class to use for uri parsing. See :mod:`uri_parsing`.
        :param validate_responses: Whether to validate responses against the specification. This has
            an impact on performance. Defaults to False.
        :param validator_map: A dictionary of validators to use. Defaults to
            :obj:`validators.VALIDATOR_MAP`.
        """
        self.middleware_app: AsyncMiddlewareApp = AsyncMiddlewareApp()

        super().__init__(
            import_name,
            specification_dir=specification_dir,
            middlewares=middlewares,
            arguments=arguments,
            auth_all_paths=auth_all_paths,
            swagger_ui_options=swagger_ui_options,
            pythonic_params=pythonic_params,
            resolver=resolver,
            resolver_error=resolver_error,
            strict_validation=strict_validation,
            uri_parser_class=uri_parser_class,
            validate_responses=validate_responses,
            validator_map=validator_map,
        )

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
