"""
This module defines a native connexion asynchronous application.
"""

import functools
import logging
import pathlib
import typing as t

from starlette.responses import Response as StarletteResponse
from starlette.routing import Router
from starlette.types import Receive, Scope, Send

from connexion.apps.abstract import AbstractApp
from connexion.decorators import StarletteDecorator
from connexion.jsonifier import Jsonifier
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware.abstract import RoutedAPI, RoutedMiddleware
from connexion.middleware.lifespan import Lifespan
from connexion.operations import AbstractOperation
from connexion.options import SwaggerUIOptions
from connexion.resolver import Resolver
from connexion.types import MaybeAwaitable
from connexion.uri_parsing import AbstractURIParser

logger = logging.getLogger(__name__)


class AsyncOperation:
    def __init__(
        self,
        fn: t.Callable,
        jsonifier: Jsonifier,
        operation_id: str,
        pythonic_params: bool,
    ) -> None:
        self._fn = fn
        self.jsonifier = jsonifier
        self.operation_id = operation_id
        self.pythonic_params = pythonic_params
        functools.update_wrapper(self, fn)

    @classmethod
    def from_operation(
        cls,
        operation: AbstractOperation,
        *,
        pythonic_params: bool,
        jsonifier: Jsonifier,
    ) -> "AsyncOperation":
        return cls(
            operation.function,
            jsonifier=jsonifier,
            operation_id=operation.operation_id,
            pythonic_params=pythonic_params,
        )

    @property
    def fn(self) -> t.Callable:
        decorator = StarletteDecorator(
            pythonic_params=self.pythonic_params,
            jsonifier=self.jsonifier,
        )
        return decorator(self._fn)

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> StarletteResponse:
        response = await self.fn()
        return await response(scope, receive, send)


class AsyncApi(RoutedAPI[AsyncOperation]):
    def __init__(
        self,
        *args,
        pythonic_params: bool,
        jsonifier: t.Optional[Jsonifier] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.pythonic_params = pythonic_params
        self.jsonifier = jsonifier or Jsonifier()
        self.router = Router()
        self.add_paths()

    def make_operation(self, operation: AbstractOperation) -> AsyncOperation:
        return AsyncOperation.from_operation(
            operation, pythonic_params=self.pythonic_params, jsonifier=self.jsonifier
        )


class AsyncASGIApp(RoutedMiddleware[AsyncApi]):

    api_cls = AsyncApi

    def __init__(self) -> None:
        self.apis: t.Dict[str, t.List[AsyncApi]] = {}
        self.operations: t.Dict[str, AsyncOperation] = {}
        self.router = Router()
        super().__init__(self.router)

    def add_api(self, *args, name: str = None, **kwargs):
        api = super().add_api(*args, **kwargs)

        if name is not None:
            self.router.mount(api.base_path, api.router, name=name)
        else:
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
        lifespan: t.Optional[Lifespan] = None,
        middlewares: t.Optional[list] = None,
        specification_dir: t.Union[pathlib.Path, str] = "",
        arguments: t.Optional[dict] = None,
        auth_all_paths: t.Optional[bool] = None,
        jsonifier: t.Optional[Jsonifier] = None,
        pythonic_params: t.Optional[bool] = None,
        resolver: t.Optional[t.Union[Resolver, t.Callable]] = None,
        resolver_error: t.Optional[int] = None,
        strict_validation: t.Optional[bool] = None,
        swagger_ui_options: t.Optional[SwaggerUIOptions] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
        validate_responses: t.Optional[bool] = None,
        validator_map: t.Optional[dict] = None,
        security_map: t.Optional[dict] = None,
    ) -> None:
        """
        :param import_name: The name of the package or module that this object belongs to. If you
            are using a single module, __name__ is always the correct value. If you however are
            using a package, it’s usually recommended to hardcode the name of your package there.
        :param lifespan: A lifespan context function, which can be used to perform startup and
            shutdown tasks.
        :param middlewares: The list of middlewares to wrap around the application. Defaults to
            :obj:`middleware.main.ConnexionMiddleware.default_middlewares`
        :param specification_dir: The directory holding the specification(s). The provided path
            should either be absolute or relative to the root path of the application. Defaults to
            the root path.
        :param arguments: Arguments to substitute the specification using Jinja.
        :param auth_all_paths: whether to authenticate not paths not defined in the specification.
            Defaults to False.
        :param jsonifier: Custom jsonifier to overwrite json encoding for json responses.
        :param pythonic_params: When True, CamelCase parameters are converted to snake_case and an
            underscore is appended to any shadowed built-ins. Defaults to False.
        :param resolver: Callable that maps operationId to a function or instance of
            :class:`resolver.Resolver`.
        :param resolver_error: Error code to return for operations for which the operationId could
            not be resolved. If no error code is provided, the application will fail when trying to
            start.
        :param strict_validation: When True, extra form or query parameters not defined in the
            specification result in a validation error. Defaults to False.
        :param swagger_ui_options: Instance of :class:`options.ConnexionOptions` with
            configuration options for the swagger ui.
        :param uri_parser_class: Class to use for uri parsing. See :mod:`uri_parsing`.
        :param validate_responses: Whether to validate responses against the specification. This has
            an impact on performance. Defaults to False.
        :param validator_map: A dictionary of validators to use. Defaults to
            :obj:`validators.VALIDATOR_MAP`.
        :param security_map: A dictionary of security handlers to use. Defaults to
            :obj:`security.SECURITY_HANDLERS`
        """
        self._middleware_app: AsyncASGIApp = AsyncASGIApp()

        super().__init__(
            import_name,
            lifespan=lifespan,
            middlewares=middlewares,
            specification_dir=specification_dir,
            arguments=arguments,
            auth_all_paths=auth_all_paths,
            jsonifier=jsonifier,
            pythonic_params=pythonic_params,
            resolver=resolver,
            resolver_error=resolver_error,
            strict_validation=strict_validation,
            swagger_ui_options=swagger_ui_options,
            uri_parser_class=uri_parser_class,
            validate_responses=validate_responses,
            validator_map=validator_map,
            security_map=security_map,
        )

    def add_url_rule(
        self, rule, endpoint: str = None, view_func: t.Callable = None, **options
    ):
        self._middleware_app.add_url_rule(
            rule, endpoint=endpoint, view_func=view_func, **options
        )

    def add_error_handler(
        self,
        code_or_exception: t.Union[int, t.Type[Exception]],
        function: t.Callable[
            [ConnexionRequest, Exception], MaybeAwaitable[ConnexionResponse]
        ],
    ) -> None:
        self.middleware.add_error_handler(code_or_exception, function)
