"""
This module defines an AbstractApp, which defines a standardized user interface for a Connexion
application.
"""
import abc
import pathlib
import typing as t

from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.jsonifier import Jsonifier
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware import ConnexionMiddleware, MiddlewarePosition, SpecMiddleware
from connexion.middleware.lifespan import Lifespan
from connexion.options import SwaggerUIOptions
from connexion.resolver import Resolver
from connexion.types import MaybeAwaitable
from connexion.uri_parsing import AbstractURIParser


class AbstractApp:
    """
    Abstract class for a Connexion Application. A Connexion Application provides an interface for a
    framework application wrapped by Connexion Middleware. Since its main function is to provide an
    interface, it delegates most of the work to the middleware and framework application.
    """

    _middleware_app: SpecMiddleware
    """
    The application wrapped by the ConnexionMiddleware, which in its turn wraps the framework
    application.
    """

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
        self.middleware = ConnexionMiddleware(
            self._middleware_app,
            import_name=import_name,
            lifespan=lifespan,
            middlewares=middlewares,
            specification_dir=specification_dir,
            arguments=arguments,
            auth_all_paths=auth_all_paths,
            jsonifier=jsonifier,
            swagger_ui_options=swagger_ui_options,
            pythonic_params=pythonic_params,
            resolver=resolver,
            resolver_error=resolver_error,
            strict_validation=strict_validation,
            uri_parser_class=uri_parser_class,
            validate_responses=validate_responses,
            validator_map=validator_map,
            security_map=security_map,
        )

    def add_middleware(
        self,
        middleware_class: t.Type[ASGIApp],
        position: MiddlewarePosition = MiddlewarePosition.BEFORE_CONTEXT,
        **options: t.Any,
    ) -> None:
        """Add a middleware to the stack on the specified position.

        :param middleware_class: Middleware class to add
        :param position: Position to add the middleware, one of the MiddlewarePosition Enum
        :param options: Options to pass to the middleware_class on initialization
        """
        self.middleware.add_middleware(middleware_class, position=position, **options)

    def add_api(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        *,
        base_path: t.Optional[str] = None,
        name: t.Optional[str] = None,
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
        **kwargs,
    ) -> t.Any:
        """
        Register an API represented by a single OpenAPI specification on this application.
        Multiple APIs can be registered on a single application.

        :param specification: OpenAPI specification. Can be provided either as dict, a path
            to file, or a URL.
        :param base_path: Base path to host the API. This overrides the basePath / servers in the
            specification.
        :param name: Name to register the API with. If no name is passed, the base_path is used
            as name instead.
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
        :param swagger_ui_options: A :class:`options.SwaggerUIOptions` instance with configuration
            options for the swagger ui.
        :param uri_parser_class: Class to use for uri parsing. See :mod:`uri_parsing`.
        :param validate_responses: Whether to validate responses against the specification. This has
            an impact on performance. Defaults to False.
        :param validator_map: A dictionary of validators to use. Defaults to
            :obj:`validators.VALIDATOR_MAP`
        :param security_map: A dictionary of security handlers to use. Defaults to
            :obj:`security.SECURITY_HANDLERS`
        :param kwargs: Additional keyword arguments to pass to the `add_api` method of the managed
            middlewares. This can be used to pass arguments to middlewares added beyond the default
            ones.

        :return: The Api registered on the middleware application wrapping the framework.
        """
        return self.middleware.add_api(
            specification,
            base_path=base_path,
            name=name,
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
            **kwargs,
        )

    def add_url_rule(
        self,
        rule,
        endpoint: t.Optional[str] = None,
        view_func: t.Optional[t.Callable] = None,
        **options,
    ):
        """
        Connects a URL rule.  Works exactly like the `route` decorator.

        Basically this example::

            @app.route('/')
            def index():
                pass

        Is equivalent to the following::

            def index():
                pass
            app.add_url_rule('/', 'index', index)

        Internally`route` invokes `add_url_rule` so if you want to customize the behavior via
        subclassing you only need to change this method.

        :param rule: the URL rule as string.
        :param endpoint: the name of the endpoint for the registered URL rule, which is used for
            reverse lookup. Flask defaults to the name of the view function.
        :param view_func: the function to call when serving a request to the provided endpoint.
        :param options: the options to be forwarded to the underlying ``werkzeug.routing.Rule``
            object.  A change to Werkzeug is handling of method options. methods is a list of
            methods this rule should be limited to (`GET`, `POST` etc.).  By default a rule just
            listens for `GET` (and implicitly `HEAD`).
        """

    def route(self, rule: str, **options):
        """
        A decorator that is used to register a view function for a
        given URL rule.  This does the same thing as `add_url_rule`
        but is intended for decorator usage::

            @app.route('/')
            def index():
                return 'Hello World'

        :param rule: the URL rule as string
        :param options: the options to be forwarded to the underlying ``werkzeug.routing.Rule``
                        object. A change to Werkzeug is handling of method options. methods is a
                        list of methods this rule should be limited to (`GET`, `POST` etc.).
                        By default a rule just listens for `GET` (and implicitly `HEAD`).
        """

        def decorator(func: t.Callable) -> t.Callable:
            self.add_url_rule(rule, view_func=func, **options)
            return func

        return decorator

    @abc.abstractmethod
    def add_error_handler(
        self,
        code_or_exception: t.Union[int, t.Type[Exception]],
        function: t.Callable[
            [ConnexionRequest, Exception], MaybeAwaitable[ConnexionResponse]
        ],
    ) -> None:
        """
        Register a callable to handle application errors.

        :param code_or_exception: An exception class or the status code of HTTP exceptions to
            handle.
        :param function: Callable that will handle exception, may be async.
        """

    def test_client(self, **kwargs):
        """Creates a test client for this application. The keywords arguments passed in are
        passed to the ``StarletteClient``."""
        return TestClient(self, **kwargs)

    def run(self, import_string: t.Optional[str] = None, **kwargs):
        """Run the application using uvicorn.

        :param import_string: application as import string (eg. "main:app"). This is needed to run
                              using reload.
        :param kwargs: kwargs to pass to `uvicorn.run`.
        """
        self.middleware.run(import_string, **kwargs)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.middleware(scope, receive, send)
