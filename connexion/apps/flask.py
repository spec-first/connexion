"""
This module defines a FlaskApp, a Connexion application to wrap a Flask application.
"""
import functools
import pathlib
import typing as t

import flask
import starlette.exceptions
import werkzeug.exceptions
from a2wsgi import WSGIMiddleware
from flask import Response as FlaskResponse
from starlette.types import Receive, Scope, Send

from connexion.apps.abstract import AbstractApp
from connexion.decorators import FlaskDecorator
from connexion.exceptions import ResolverError
from connexion.frameworks import flask as flask_utils
from connexion.jsonifier import Jsonifier
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware.abstract import AbstractRoutingAPI, SpecMiddleware
from connexion.middleware.lifespan import Lifespan
from connexion.operations import AbstractOperation
from connexion.options import SwaggerUIOptions
from connexion.resolver import Resolver
from connexion.types import MaybeAwaitable, WSGIApp
from connexion.uri_parsing import AbstractURIParser


class FlaskOperation:
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
    ) -> "FlaskOperation":
        return cls(
            fn=operation.function,
            jsonifier=jsonifier,
            operation_id=operation.operation_id,
            pythonic_params=pythonic_params,
        )

    @property
    def fn(self) -> t.Callable:
        decorator = FlaskDecorator(
            pythonic_params=self.pythonic_params,
            jsonifier=self.jsonifier,
        )
        return decorator(self._fn)

    def __call__(self, *args, **kwargs) -> FlaskResponse:
        return self.fn(*args, **kwargs)


class FlaskApi(AbstractRoutingAPI):
    def __init__(
        self, *args, jsonifier: t.Optional[Jsonifier] = None, **kwargs
    ) -> None:
        self.jsonifier = jsonifier or Jsonifier(flask.json, indent=2)
        super().__init__(*args, **kwargs)

    def _set_base_path(self, base_path: t.Optional[str] = None) -> None:
        super()._set_base_path(base_path)
        self._set_blueprint()

    def _set_blueprint(self):
        endpoint = flask_utils.flaskify_endpoint(self.base_path) or "/"
        self.blueprint = flask.Blueprint(
            endpoint,
            __name__,
            url_prefix=self.base_path,
        )

    def _add_resolver_error_handler(self, method: str, path: str, err: ResolverError):
        pass

    def make_operation(self, operation):
        return FlaskOperation.from_operation(
            operation, pythonic_params=self.pythonic_params, jsonifier=self.jsonifier
        )

    @staticmethod
    def _framework_path_and_name(
        operation: AbstractOperation, path: str
    ) -> t.Tuple[str, str]:
        flask_path = flask_utils.flaskify_path(
            path, operation.get_path_parameter_types()
        )
        endpoint_name = flask_utils.flaskify_endpoint(
            operation.operation_id, operation.randomize_endpoint
        )
        return flask_path, endpoint_name

    def _add_operation_internal(
        self,
        method: str,
        path: str,
        operation: t.Callable,
        name: t.Optional[str] = None,
    ) -> None:
        self.blueprint.add_url_rule(path, name, operation, methods=[method])

    def add_url_rule(
        self,
        rule,
        endpoint: t.Optional[str] = None,
        view_func: t.Optional[t.Callable] = None,
        **options,
    ):
        return self.blueprint.add_url_rule(rule, endpoint, view_func, **options)


class FlaskASGIApp(SpecMiddleware):
    def __init__(self, import_name, server_args: dict, **kwargs):
        self.app = flask.Flask(import_name, **server_args)
        self.app.json = flask_utils.FlaskJSONProvider(self.app)
        self.app.url_map.converters["float"] = flask_utils.NumberConverter
        self.app.url_map.converters["int"] = flask_utils.IntegerConverter

        # Propagate Errors so we can handle them in the middleware
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.app.config["TRAP_BAD_REQUEST_ERRORS"] = True
        self.app.config["TRAP_HTTP_EXCEPTIONS"] = True

        self.asgi_app = WSGIMiddleware(self.app.wsgi_app)

    def add_api(self, specification, *, name: t.Optional[str] = None, **kwargs):
        api = FlaskApi(specification, **kwargs)

        if name is not None:
            self.app.register_blueprint(api.blueprint, name=name)
        else:
            self.app.register_blueprint(api.blueprint)

        return api

    def add_url_rule(
        self,
        rule,
        endpoint: t.Optional[str] = None,
        view_func: t.Optional[t.Callable] = None,
        **options,
    ):
        return self.app.add_url_rule(rule, endpoint, view_func, **options)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.asgi_app(scope, receive, send)


class FlaskApp(AbstractApp):
    """Connexion Application based on ConnexionMiddleware wrapping a Flask application."""

    _middleware_app: FlaskASGIApp

    def __init__(
        self,
        import_name: str,
        *,
        lifespan: t.Optional[Lifespan] = None,
        middlewares: t.Optional[list] = None,
        server_args: t.Optional[dict] = None,
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
    ):
        """
        :param import_name: The name of the package or module that this object belongs to. If you
            are using a single module, __name__ is always the correct value. If you however are
            using a package, it’s usually recommended to hardcode the name of your package there.
        :param lifespan: A lifespan context function, which can be used to perform startup and
            shutdown tasks.
        :param middlewares: The list of middlewares to wrap around the application. Defaults to
            :obj:`middleware.main.ConnexionMiddleware.default_middlewares`
        :param server_args: Arguments to pass to the Flask application.
        :param specification_dir: The directory holding the specification(s). The provided path
            should either be absolute or relative to the root path of the application. Defaults to
            the root path.
        :param arguments: Arguments to substitute the specification using Jinja.
        :param auth_all_paths: whether to authenticate all paths not defined in the specification.
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
        :param swagger_ui_options: Instance of :class:`options.SwaggerUIOptions` with
            configuration options for the swagger ui.
        :param uri_parser_class: Class to use for uri parsing. See :mod:`uri_parsing`.
        :param validate_responses: Whether to validate responses against the specification. This has
            an impact on performance. Defaults to False.
        :param validator_map: A dictionary of validators to use. Defaults to
            :obj:`validators.VALIDATOR_MAP`.
        :param security_map: A dictionary of security handlers to use. Defaults to
            :obj:`security.SECURITY_HANDLERS`
        """
        self._middleware_app = FlaskASGIApp(import_name, server_args or {})

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

        self.app = self._middleware_app.app
        self.app.register_error_handler(
            werkzeug.exceptions.HTTPException, self._http_exception
        )

    def _http_exception(self, exc: werkzeug.exceptions.HTTPException):
        """Reraise werkzeug HTTPExceptions as starlette HTTPExceptions"""
        raise starlette.exceptions.HTTPException(exc.code, detail=exc.description)

    def add_url_rule(
        self,
        rule,
        endpoint: t.Optional[str] = None,
        view_func: t.Optional[t.Callable] = None,
        **options,
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

    def add_wsgi_middleware(
        self, middleware: t.Type[WSGIApp], **options: t.Any
    ) -> None:
        """Wrap the underlying Flask application with a WSGI middleware. Note that it will only be
        called at the end of the middleware stack. Middleware that needs to act sooner, needs to
        be added as ASGI middleware instead.

        Adding multiple middleware using this method wraps each middleware around the previous one.

        :param middleware: Middleware class to add
        :param options: Options to pass to the middleware_class on initialization
        """
        self._middleware_app.asgi_app.app = middleware(
            self._middleware_app.asgi_app.app, **options  # type: ignore
        )
