import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send


class ConnexionMiddleware:

    default_middlewares = [
    ]

    def __init__(
            self,
            app: ASGIApp,
            middlewares: t.Optional[t.List[t.Type[ASGIApp]]] = None
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

        self._routing_middleware = None

    @staticmethod
    def _apply_middlewares(app: ASGIApp, middlewares: t.List[t.Type[ASGIApp]]) \
            -> t.Tuple[ASGIApp, t.Iterable[ASGIApp]]:
        """Apply all middlewares to the provided app.

        :param app: App to wrap in middlewares.
        :param middlewares: List of middlewares to wrap around app. The list should be ordered
                            from outer to inner middleware.

        :return: App with all middlewares applied.
        """
        apps = []
        for middleware in reversed(middlewares):
            app = middleware(app)
            apps.append(app)
        return app, reversed(apps)

    def add_api(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
    ) -> None:
        """Add an API to the underlying routing middleware based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)
