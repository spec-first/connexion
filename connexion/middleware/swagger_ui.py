import json
import logging
import re
import typing as t
from contextvars import ContextVar

from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.routing import Router
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.jsonifier import Jsonifier
from connexion.middleware import SpecMiddleware
from connexion.middleware.abstract import AbstractSpecAPI
from connexion.options import SwaggerUIConfig, SwaggerUIOptions
from connexion.spec import Specification
from connexion.utils import yamldumper

logger = logging.getLogger("connexion.middleware.swagger_ui")


_original_scope: ContextVar[Scope] = ContextVar("SCOPE")


class SwaggerUIAPI(AbstractSpecAPI):
    def __init__(
        self,
        *args,
        default: ASGIApp,
        swagger_ui_options: t.Optional[SwaggerUIOptions] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.router = Router(default=default)
        self.options = SwaggerUIConfig(
            swagger_ui_options, oas_version=self.specification.version
        )

        if self.options.openapi_spec_available:
            self.add_openapi_json()
            self.add_openapi_yaml()

        if self.options.swagger_ui_available:
            self.add_swagger_ui()

        self._templates = Jinja2Templates(
            directory=str(self.options.swagger_ui_template_dir)
        )

    @staticmethod
    def normalize_string(string):
        return re.sub(r"[^a-zA-Z0-9]", "_", string.strip("/"))

    def _base_path_for_prefix(self, request: StarletteRequest) -> str:
        """
        returns a modified basePath which includes the incoming root_path.
        """
        return request.scope.get(
            "route_root_path", request.scope.get("root_path", "")
        ).rstrip("/")

    def _spec_for_prefix(self, request):
        """
        returns a spec with a modified basePath / servers block
        which corresponds to the incoming request path.
        This is needed when behind a path-altering reverse proxy.
        """
        base_path = self._base_path_for_prefix(request)
        return self.specification.with_base_path(base_path).raw

    def add_openapi_json(self):
        """
        Adds openapi json to {base_path}/openapi.json
             (or {base_path}/swagger.json for swagger2)
        """
        logger.info(
            "Adding spec json: %s%s", self.base_path, self.options.openapi_spec_path
        )
        self.router.add_route(
            methods=["GET"],
            path=self.options.openapi_spec_path,
            endpoint=self._get_openapi_json,
        )

    def add_openapi_yaml(self):
        """
        Adds openapi json to {base_path}/openapi.json
             (or {base_path}/swagger.json for swagger2)
        """
        if not self.options.openapi_spec_path.endswith("json"):
            return

        openapi_spec_path_yaml = self.options.openapi_spec_path[: -len("json")] + "yaml"
        logger.debug("Adding spec yaml: %s/%s", self.base_path, openapi_spec_path_yaml)
        self.router.add_route(
            methods=["GET"],
            path=openapi_spec_path_yaml,
            endpoint=self._get_openapi_yaml,
        )

    async def _get_openapi_json(self, request):
        # Yaml parses datetime objects when loading the spec, so we need our custom jsonifier to dump it
        jsonifier = Jsonifier()

        return StarletteResponse(
            content=jsonifier.dumps(self._spec_for_prefix(request)),
            status_code=200,
            media_type="application/json",
        )

    async def _get_openapi_yaml(self, request):
        return StarletteResponse(
            content=yamldumper(self._spec_for_prefix(request)),
            status_code=200,
            media_type="text/yaml",
        )

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_path}/ui/
        """
        console_ui_path = self.options.swagger_ui_path.strip().rstrip("/")
        logger.debug("Adding swagger-ui: %s%s/", self.base_path, console_ui_path)

        for path in (
            console_ui_path + "/",
            console_ui_path + "/index.html",
        ):
            self.router.add_route(
                methods=["GET"], path=path, endpoint=self._get_swagger_ui_home
            )

        if self.options.swagger_ui_config:
            self.router.add_route(
                methods=["GET"],
                path=console_ui_path + "/swagger-ui-config.json",
                endpoint=self._get_swagger_ui_config,
            )

        # we have to add an explicit redirect instead of relying on the
        # normalize_path_middleware because we also serve static files
        # from this dir (below)

        async def redirect(request):
            url = request.scope.get("root_path", "").rstrip("/")
            url += console_ui_path
            url += "/"
            return RedirectResponse(url=url)

        self.router.add_route(methods=["GET"], path=console_ui_path, endpoint=redirect)

        # this route will match and get a permission error when trying to
        # serve index.html, so we add the redirect above.
        self.router.mount(
            path=console_ui_path,
            app=StaticFiles(directory=str(self.options.swagger_ui_template_dir)),
            name="swagger_ui_static",
        )

    async def _get_swagger_ui_home(self, req):
        base_path = self._base_path_for_prefix(req)
        template_variables = {
            "request": req,
            "openapi_spec_url": (base_path + self.options.openapi_spec_path),
            **self.options.swagger_ui_template_arguments,
        }
        if self.options.swagger_ui_config:
            template_variables["configUrl"] = "swagger-ui-config.json"

        return self._templates.TemplateResponse("index.j2", template_variables)

    async def _get_swagger_ui_config(self, request):
        return StarletteResponse(
            status_code=200,
            media_type="application/json",
            content=json.dumps(self.options.swagger_ui_config),
        )


class SwaggerUIMiddleware(SpecMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        """Middleware that hosts a swagger UI.

        :param app: app to wrap in middleware.
        """
        self.app = app
        # Set default to pass unknown routes to next app
        self.router = Router(default=self.default_fn)

    def add_api(
        self,
        specification: Specification,
        base_path: t.Optional[str] = None,
        arguments: t.Optional[dict] = None,
        **kwargs
    ) -> None:
        """Add an API to the router based on a OpenAPI spec.

        :param specification: OpenAPI spec.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        api = SwaggerUIAPI(
            specification,
            base_path=base_path,
            arguments=arguments,
            default=self.default_fn,
            **kwargs
        )
        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        _original_scope.set(scope.copy())  # type: ignore
        await self.router(scope, receive, send)

    async def default_fn(self, _scope: Scope, receive: Receive, send: Send) -> None:
        """
        Callback to call next app as default when no matching route is found.

        Unfortunately we cannot just pass the next app as default, since the router manipulates
        the scope when descending into mounts, losing information about the base path. Therefore,
        we use the original scope instead.

        This is caused by https://github.com/encode/starlette/issues/1336.
        """
        original_scope = _original_scope.get()
        await self.app(original_scope, receive, send)
