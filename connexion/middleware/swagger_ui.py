import pathlib
import typing as t

from starlette.routing import Router
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.middleware_api import SwaggerUIAPI


class SwaggerUIMiddleware:

    def __init__(self, app: ASGIApp) -> None:
        """Middleware that hosts a swagger UI.

        :param app: app to wrap in middleware.
        """
        self.app = app
        # Pass unknown routes to next app
        self.router = Router(default=self.app)

    def add_api(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
    ) -> None:
        """Add an API to the router based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        api = SwaggerUIAPI(specification, base_path=base_path, arguments=arguments,
                           default=self.app)
        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.router(scope, receive, send)
