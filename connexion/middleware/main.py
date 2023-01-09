import logging
import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion import utils
from connexion.middleware.abstract import AppMiddleware
from connexion.middleware.context import ContextMiddleware
from connexion.middleware.exceptions import ExceptionMiddleware
from connexion.middleware.request_validation import RequestValidationMiddleware
from connexion.middleware.response_validation import ResponseValidationMiddleware
from connexion.middleware.routing import RoutingMiddleware
from connexion.middleware.security import SecurityMiddleware
from connexion.middleware.swagger_ui import SwaggerUIMiddleware
from connexion.resolver import Resolver

logger = logging.getLogger(__name__)


class ConnexionMiddleware:

    default_middlewares = [
        ExceptionMiddleware,
        SwaggerUIMiddleware,
        RoutingMiddleware,
        SecurityMiddleware,
        RequestValidationMiddleware,
        ResponseValidationMiddleware,
        ContextMiddleware,
    ]

    def __init__(
        self,
        app: ASGIApp,
        *,
        import_name: str = None,
        specification_dir: t.Union[pathlib.Path, str] = "",
        resolver: Resolver = None,
        middlewares: t.Optional[t.List[t.Type[ASGIApp]]] = None,
    ):
        """High level Connexion middleware that manages a list o middlewares wrapped around an
        application.

        :param app: App to wrap middleware around.
        :param specification_dir: directory where to look for specifications
        :param middlewares: List of middlewares to wrap around app. The list should be ordered
                            from outer to inner middleware.
        """
        self.import_name = import_name or str(pathlib.Path.cwd())
        self.resolver = resolver
        self.extra_files: t.List[str] = []

        if middlewares is None:
            middlewares = self.default_middlewares
        self.app, self.apps = self._apply_middlewares(app, middlewares)

        self.root_path = utils.get_root_path(self.import_name)

        specification_dir = pathlib.Path(
            specification_dir
        )  # Ensure specification dir is a Path
        if specification_dir.is_absolute():
            self.specification_dir = specification_dir
        else:
            self.specification_dir = self.root_path / specification_dir

    @staticmethod
    def _apply_middlewares(
        app: ASGIApp, middlewares: t.List[t.Type[ASGIApp]]
    ) -> t.Tuple[ASGIApp, t.Iterable[ASGIApp]]:
        """Apply all middlewares to the provided app.

        :param app: App to wrap in middlewares.
        :param middlewares: List of middlewares to wrap around app. The list should be ordered
                            from outer to inner middleware.

        :return: App with all middlewares applied.
        """
        apps = []
        for middleware in reversed(middlewares):
            app = middleware(app)  # type: ignore
            apps.append(app)
        return app, list(reversed(apps))

    def add_api(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        base_path: t.Optional[str] = None,
        arguments: t.Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Add an API to the underlying routing middleware based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
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

        for app in self.apps:
            if isinstance(app, AppMiddleware):
                app.add_api(
                    specification,
                    base_path=base_path,
                    arguments=arguments,
                    resolver=self.resolver,
                    **kwargs,
                )

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
