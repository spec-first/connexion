import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.middleware.abstract import AppMiddleware
from connexion.middleware.exceptions import ExceptionMiddleware
from connexion.middleware.routing import RoutingMiddleware
from connexion.middleware.security import SecurityMiddleware
from connexion.middleware.swagger_ui import SwaggerUIMiddleware


class ConnexionMiddleware:

    default_middlewares = [
        ExceptionMiddleware,
        SwaggerUIMiddleware,
        RoutingMiddleware,
        SecurityMiddleware,
    ]

    def __init__(
        self, app: ASGIApp, middlewares: t.Optional[t.List[t.Type[ASGIApp]]] = None
    ):
        """High level Connexion middleware that manages a list o middlewares wrapped around an
        application.

        :param app: App to wrap middleware around.
        :param middlewares: List of middlewares to wrap around app. The list should be ordered
                            from outer to inner middleware.
        """
        if middlewares is None:
            middlewares = self.default_middlewares
        self.app, self.apps = self._apply_middlewares(app, middlewares)

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
        return app, reversed(apps)

    def add_api(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        base_path: t.Optional[str] = None,
        arguments: t.Optional[dict] = None,
        **kwargs
    ) -> None:
        """Add an API to the underlying routing middleware based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        for app in self.apps:
            if isinstance(app, AppMiddleware):
                app.add_api(
                    specification, base_path=base_path, arguments=arguments, **kwargs
                )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)
