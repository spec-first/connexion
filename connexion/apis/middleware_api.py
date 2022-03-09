import logging
import pathlib
import re
import typing as t

from starlette.responses import RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.routing import Router
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp

from connexion.apis import AbstractMinimalAPI, AbstractSwaggerUIAPI
from connexion.operations import AbstractOperation, make_operation
from connexion.resolver import Resolver
from connexion.security import MiddlewareSecurityHandlerFactory
from connexion.utils import yamldumper

logger = logging.getLogger('connexion.apis.middleware')


class MiddlewareAPI(AbstractMinimalAPI):

    def __init__(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
            resolver: t.Optional[Resolver] = None,
            resolver_error_handler: t.Optional[t.Callable] = None,
            debug: bool = False,
    ) -> None:
        """API implementation on top of Starlette Router for Connexion middleware."""
        self.router = Router()

        super().__init__(
            specification,
            base_path=base_path,
            arguments=arguments,
            resolver=resolver,
            resolver_error_handler=resolver_error_handler,
            debug=debug
        )

    def add_operation(self, path: str, method: str) -> None:
        operation = make_operation(
            self.specification,
            self,
            path,
            method,
            self.resolver
        )
        # Don't set decorators in middleware
        AbstractOperation.function = operation._resolution.function
        self._add_operation_internal(method, path, operation)

    def _add_operation_internal(self, method: str, path: str, operation: AbstractOperation) -> None:
        self.router.add_route(path, operation.function, methods=[method])

    @staticmethod
    def make_security_handler_factory(pass_context_arg_name):
        """ Create default SecurityHandlerFactory to create all security check handlers """
        return MiddlewareSecurityHandlerFactory(pass_context_arg_name)


class SwaggerUIAPI(AbstractSwaggerUIAPI):

    def __init__(self, *args, default: ASGIApp, **kwargs):
        self.router = Router(default=default)

        super().__init__(*args, **kwargs)

        self._templates = Jinja2Templates(
            directory=str(self.options.openapi_console_ui_from_dir)
        )

    @staticmethod
    def normalize_string(string):
        return re.sub(r"[^a-zA-Z0-9]", "_", string.strip("/"))

    def _base_path_for_prefix(self, request):
        """
        returns a modified basePath which includes the incoming request's
        path prefix.
        """
        base_path = self.base_path
        if not request.url.path.startswith(self.base_path):
            prefix = request.url.path.split(self.base_path)[0]
            base_path = prefix + base_path
        return base_path

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
            "Adding spec json: %s/%s", self.base_path, self.options.openapi_spec_path
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
        return StarletteResponse(
            content=self.jsonifier.dumps(self._spec_for_prefix(request)),
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
        console_ui_path = self.options.openapi_console_ui_path.strip().rstrip("/")
        logger.debug("Adding swagger-ui: %s%s/", self.base_path, console_ui_path)

        for path in (
            console_ui_path + "/",
            console_ui_path + "/index.html",
        ):
            self.router.add_route(
                methods=["GET"], path=path, endpoint=self._get_swagger_ui_home
            )

        if self.options.openapi_console_ui_config is not None:
            self.router.add_route(
                methods=["GET"],
                path=console_ui_path + "/swagger-ui-config.json",
                endpoint=self._get_swagger_ui_config,
            )

        # we have to add an explicit redirect instead of relying on the
        # normalize_path_middleware because we also serve static files
        # from this dir (below)

        async def redirect(request):
            return RedirectResponse(url=self.base_path + console_ui_path + "/")

        self.router.add_route(methods=["GET"], path=console_ui_path, endpoint=redirect)

        # this route will match and get a permission error when trying to
        # serve index.html, so we add the redirect above.
        self.router.mount(
            path=console_ui_path,
            app=StaticFiles(directory=str(self.options.openapi_console_ui_from_dir)),
            name="swagger_ui_static",
        )

    async def _get_swagger_ui_home(self, req):
        base_path = self._base_path_for_prefix(req)
        template_variables = {
            "request": req,
            "openapi_spec_url": (base_path + self.options.openapi_spec_path),
            **self.options.openapi_console_ui_index_template_variables,
        }
        if self.options.openapi_console_ui_config is not None:
            template_variables["configUrl"] = "swagger-ui-config.json"

        return self._templates.TemplateResponse("index.j2", template_variables)

    async def _get_swagger_ui_config(self, request):
        return StarletteResponse(
            status_code=200,
            media_type="application/json",
            content=self.jsonifier.dumps(self.options.openapi_console_ui_config),
        )
