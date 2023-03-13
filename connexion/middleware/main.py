import dataclasses
import logging
import pathlib
import typing as t
from dataclasses import dataclass, field

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion import utils
from connexion.handlers import ResolverErrorHandler
from connexion.jsonifier import Jsonifier
from connexion.middleware.abstract import SpecMiddleware
from connexion.middleware.context import ContextMiddleware
from connexion.middleware.exceptions import ExceptionMiddleware
from connexion.middleware.lifespan import Lifespan, LifespanMiddleware
from connexion.middleware.request_validation import RequestValidationMiddleware
from connexion.middleware.response_validation import ResponseValidationMiddleware
from connexion.middleware.routing import RoutingMiddleware
from connexion.middleware.security import SecurityMiddleware
from connexion.middleware.swagger_ui import SwaggerUIMiddleware
from connexion.resolver import Resolver
from connexion.uri_parsing import AbstractURIParser

logger = logging.getLogger(__name__)


@dataclass
class _Options:
    """
    Connexion provides a lot of parameters for the user to configure the app / middleware of
    application.

    This class provides a central place to parse these parameters a mechanism to update them.
    Application level arguments can be provided when instantiating the application / middleware,
    after which they can be overwritten on an API level.

    The defaults should only be set in this class, and set to None in the signature of user facing
    methods. This is necessary for this class to be able to differentiate between missing and
    falsy arguments.
    """

    arguments: t.Optional[dict] = None
    auth_all_paths: t.Optional[bool] = False
    jsonifier: t.Optional[Jsonifier] = None
    pythonic_params: t.Optional[bool] = False
    resolver: t.Optional[t.Union[Resolver, t.Callable]] = None
    resolver_error: t.Optional[int] = None
    resolver_error_handler: t.Optional[t.Callable] = field(init=False)
    strict_validation: t.Optional[bool] = False
    swagger_ui_options: t.Optional[dict] = None
    uri_parser_class: t.Optional[AbstractURIParser] = None
    validate_responses: t.Optional[bool] = False
    validator_map: t.Optional[dict] = None

    def __post_init__(self):
        self.resolver = (
            Resolver(self.resolver) if callable(self.resolver) else self.resolver
        )
        self.resolver_error_handler = self._resolver_error_handler_factory()

    def _resolver_error_handler_factory(
        self,
    ) -> t.Optional[t.Callable[[], ResolverErrorHandler]]:
        """Returns a factory to create a ResolverErrorHandler."""
        if self.resolver_error is not None:

            def resolver_error_handler(*args, **kwargs) -> ResolverErrorHandler:
                return ResolverErrorHandler(self.resolver_error, *args, **kwargs)

            return resolver_error_handler
        return None

    def replace(self, **changes) -> "_Options":
        """Update mechanism to overwrite the options. None values are discarded.

        :param changes: Arguments accepted by the __init__ method of this class.

        :return: An new _Options object with updated arguments.
        """
        changes = {key: value for key, value in changes.items() if value is not None}
        return dataclasses.replace(self, **changes)


class ConnexionMiddleware:
    """The main Connexion middleware, which wraps a list of specialized middlewares around the
    provided application."""

    default_middlewares = [
        ExceptionMiddleware,
        SwaggerUIMiddleware,
        RoutingMiddleware,
        SecurityMiddleware,
        RequestValidationMiddleware,
        ResponseValidationMiddleware,
        ContextMiddleware,
        LifespanMiddleware,
    ]

    def __init__(
        self,
        app: ASGIApp,
        *,
        import_name: t.Optional[str] = None,
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
        swagger_ui_options: t.Optional[dict] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
        validate_responses: t.Optional[bool] = None,
        validator_map: t.Optional[dict] = None,
    ):
        """
        :param import_name: The name of the package or module that this object belongs to. If you
            are using a single module, __name__ is always the correct value. If you however are
            using a package, it’s usually recommended to hardcode the name of your package there.
        :param middlewares: The list of middlewares to wrap around the application. Defaults to
            :obj:`middleware.main.ConnexionmMiddleware.default_middlewares`
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
        :param swagger_ui_options: A :class:`options.ConnexionOptions` instance with configuration
            options for the swagger ui.
        :param uri_parser_class: Class to use for uri parsing. See :mod:`uri_parsing`.
        :param validate_responses: Whether to validate responses against the specification. This has
            an impact on performance. Defaults to False.
        :param validator_map: A dictionary of validators to use. Defaults to
            :obj:`validators.VALIDATOR_MAP`.
        """
        import_name = import_name or str(pathlib.Path.cwd())
        self.root_path = utils.get_root_path(import_name)

        self.specification_dir = self.ensure_absolute(specification_dir)

        if middlewares is None:
            middlewares = self.default_middlewares
        self.app, self.apps = self._apply_middlewares(
            app, middlewares, lifespan=lifespan
        )

        self.options = _Options(
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
        )

        self.extra_files: t.List[str] = []

    def ensure_absolute(self, path: t.Union[str, pathlib.Path]) -> pathlib.Path:
        """Ensure that a path is absolute. If the path is not absolute, it is assumed to relative
        to the application root path and made absolute."""
        path = pathlib.Path(path)
        if path.is_absolute():
            return path
        else:
            return self.root_path / path

    def _apply_middlewares(
        self, app: ASGIApp, middlewares: t.List[t.Type[ASGIApp]], **kwargs
    ) -> t.Tuple[ASGIApp, t.Iterable[ASGIApp]]:
        """Apply all middlewares to the provided app.

        :param app: App to wrap in middlewares.
        :param middlewares: List of middlewares to wrap around app. The list should be ordered
                            from outer to inner middleware.

        :return: Tuple of the outer middleware wrapping the application and a list of the wrapped
            middlewares, including the wrapped application.
        """
        # Include the wrapped application in the returned list.
        apps = [app]
        for middleware in reversed(middlewares):
            app = middleware(app, **kwargs)  # type: ignore
            apps.append(app)
        return app, list(reversed(apps))

    def add_api(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        *,
        base_path: t.Optional[str] = None,
        arguments: t.Optional[dict] = None,
        auth_all_paths: t.Optional[bool] = None,
        jsonifier: t.Optional[Jsonifier] = None,
        pythonic_params: t.Optional[bool] = None,
        resolver: t.Optional[t.Union[Resolver, t.Callable]] = None,
        resolver_error: t.Optional[int] = None,
        strict_validation: t.Optional[bool] = None,
        swagger_ui_options: t.Optional[dict] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
        validate_responses: t.Optional[bool] = None,
        validator_map: t.Optional[dict] = None,
        **kwargs,
    ) -> t.Any:
        """
        Register een API represented by a single OpenAPI specification on this middleware.
        Multiple APIs can be registered on a single middleware.

        :param specification: OpenAPI specification. Can be provided either as dict, or as path
            to file.
        :param base_path: Base path to host the API. This overrides the basePath / servers in the
            specification.
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
        :param swagger_ui_options: A :class:`options.ConnexionOptions` instance with configuration
            options for the swagger ui.
        :param uri_parser_class: Class to use for uri parsing. See :mod:`uri_parsing`.
        :param validate_responses: Whether to validate responses against the specification. This has
            an impact on performance. Defaults to False.
        :param validator_map: A dictionary of validators to use. Defaults to
            :obj:`validators.VALIDATOR_MAP`
        :param kwargs: Additional keyword arguments to pass to the `add_api` method of the managed
            middlewares. This can be used to pass arguments to middlewares added beyond the default
            ones.

        :return: The Api registered on the wrapped application.
        """
        if isinstance(specification, dict):
            specification = specification
        else:
            specification = t.cast(pathlib.Path, self.specification_dir / specification)
            # Add specification as file to watch for reloading
            if pathlib.Path.cwd() in specification.parents:
                self.extra_files.append(
                    str(specification.relative_to(pathlib.Path.cwd()))
                )

        options = self.options.replace(
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
        )

        for app in self.apps:
            if isinstance(app, SpecMiddleware):
                api = app.add_api(
                    specification,
                    base_path=base_path,
                    **options.__dict__,
                    **kwargs,
                )

        # Api registered on the inner application.
        return api

    def add_error_handler(
        self, code_or_exception: t.Union[int, t.Type[Exception]], function: t.Callable
    ) -> None:
        for app in self.apps:
            if isinstance(app, ExceptionMiddleware):
                app.add_exception_handler(code_or_exception, function)

    def run(self, import_string: str = None, **kwargs):
        """Run the application using uvicorn.

        :param import_string: application as import string (eg. "main:app"). This is needed to run
                              using reload.
        :param kwargs: kwargs to pass to `uvicorn.run`.
        """
        try:
            import uvicorn
        except ImportError:
            raise RuntimeError(
                "uvicorn is not installed. Please install connexion using the uvicorn extra "
                "(connexion[uvicorn])"
            )

        logger.warning(
            f"`{self.__class__.__name__}.run` is optimized for development. "
            "For production, run using a dedicated ASGI server."
        )

        app: t.Union[str, ConnexionMiddleware]
        if import_string is not None:
            app = import_string
            kwargs.setdefault("reload", True)
            kwargs["reload_includes"] = self.extra_files + kwargs.get(
                "reload_includes", []
            )
        else:
            app = self

        uvicorn.run(app, **kwargs)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)
