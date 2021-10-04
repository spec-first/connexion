"""
This module defines an Starlette Connexion API which implements translations between ASGI and
Connexion requests / responses.
"""

import asyncio
import logging
import re
from urllib.parse import parse_qs

from starlette.responses import RedirectResponse, Response
from starlette.routing import Router
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from werkzeug.exceptions import NotFound

from connexion.apis.abstract import AbstractAPI
from connexion.handlers import AuthErrorHandler
from connexion.jsonifier import JSONEncoder, Jsonifier
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.security import AioHttpSecurityHandlerFactory
from connexion.utils import yamldumper

logger = logging.getLogger("connexion.apis.starlette_api")


class StarletteApi(AbstractAPI):
    def __init__(self, *args, **kwargs):
        self.subapp: Router = Router()

        AbstractAPI.__init__(self, *args, **kwargs)

        self._templates = Jinja2Templates(
            directory=str(self.options.openapi_console_ui_from_dir)
        )

    @staticmethod
    def make_security_handler_factory(pass_context_arg_name):
        """ Create default SecurityHandlerFactory to create all security check handlers """
        return AioHttpSecurityHandlerFactory(pass_context_arg_name)

    def _set_base_path(self, base_path):
        AbstractAPI._set_base_path(self, base_path)
        self._api_name = StarletteApi.normalize_string(self.base_path)

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
        logger.debug(
            "Adding spec json: %s/%s", self.base_path, self.options.openapi_spec_path
        )
        self.subapp.add_route(
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
        self.subapp.add_route(
            methods=["GET"],
            path=openapi_spec_path_yaml,
            endpoint=self._get_openapi_yaml,
        )

    async def _get_openapi_json(self, request):
        return Response(
            content=self.jsonifier.dumps(self._spec_for_prefix(request)),
            status_code=200,
            media_type="application/json",
        )

    async def _get_openapi_yaml(self, request):
        return Response(
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
            self.subapp.add_route(
                methods=["GET"], path=path, endpoint=self._get_swagger_ui_home
            )

        if self.options.openapi_console_ui_config is not None:
            self.subapp.add_route(
                methods=["GET"],
                path=console_ui_path + "/swagger-ui-config.json",
                endpoint=self._get_swagger_ui_config,
            )

        # we have to add an explicit redirect instead of relying on the
        # normalize_path_middleware because we also serve static files
        # from this dir (below)

        async def redirect(request):
            return RedirectResponse(url=self.base_path + console_ui_path + "/")

        self.subapp.add_route(methods=["GET"], path=console_ui_path, endpoint=redirect)

        # this route will match and get a permission error when trying to
        # serve index.html, so we add the redirect above.
        self.subapp.mount(
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
        return Response(
            status_code=200,
            media_type="text/json",
            content=self.jsonifier.dumps(self.options.openapi_console_ui_config),
        )

    def add_auth_on_not_found(self, security, security_definitions):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug("Adding path not found authentication")
        not_found_error = AuthErrorHandler(
            self,
            NotFound(),
            security=security,
            security_definitions=security_definitions,
        )
        endpoint_name = f"{self._api_name}_not_found"
        self.subapp.add_route(
            path="/{not_found_path}",
            endpoint=not_found_error.function,
            name=endpoint_name,
        )

    def _add_operation_internal(self, method, path, operation):
        method = method.upper()
        operation_id = operation.operation_id or path

        logger.debug("... Adding %s -> %s", method, operation_id, extra=vars(operation))

        handler = operation.function
        endpoint_name = "{}_{}_{}".format(
            self._api_name, StarletteApi.normalize_string(path), method.lower()
        )
        self.subapp.add_route(
            methods=[method], path=path, endpoint=handler, name=endpoint_name
        )

        if not path.endswith("/"):
            self.subapp.add_route(
                methods=[method],
                path=path + "/",
                endpoint=handler,
                name=endpoint_name + "_",
            )

    @classmethod
    async def get_request(cls, req):
        """Convert Starlette request to connexion

        :param req: instance of aiohttp.web.Request
        :return: connexion request instance
        :rtype: ConnexionRequest
        """
        url = str(req.url)
        logger.debug("Getting data and status code", extra={"url": url})
        query = parse_qs(req.url.query)

        # Empty body <=> no body
        body = await req.body()
        if not body:
            body = None

        # TODO: setup `context` properly
        # TODO: setup `headers` properly
        headers = req.headers
        # TODO: setup `path_params` properly

        return ConnexionRequest(
            url=url,
            method=req.method.lower(),
            path_params=dict(req.path_params),
            query=query,
            headers=headers,
            body=body,
            json_getter=lambda: cls.jsonifier.loads(body),
            files={},
        )

    @classmethod
    async def get_response(cls, response, mimetype=None, request=None):
        """Get response.
        This method is used in the lifecycle decorators

        :type response: starlette.responses.Response | (Any,) | (Any, int) | (Any, dict) | (Any, int, dict)
        :rtype: starlette.responses.Response
        """
        while asyncio.iscoroutine(response):
            response = await response
        url = str(request.url) if request else ""

        return cls._get_response(
            response, mimetype=mimetype, extra_context={"url": url}
        )

    @classmethod
    def _is_framework_response(cls, response):
        """ Return True if `response` is a framework response class """
        return isinstance(response, Response)

    @classmethod
    def _framework_to_connexion_response(cls, response, mimetype):
        """ Cast framework response class to ConnexionResponse used for schema validation """

        # FileResponse and StreamingResponse do not a `body` (yet)
        body = None
        if hasattr(response, 'body'):
            body = response.body

        return ConnexionResponse(
            status_code=response.status_code,
            mimetype=mimetype,
            content_type=response.media_type,
            headers=response.headers,
            body=body,
        )

    @classmethod
    def _connexion_to_framework_response(cls, response, mimetype, extra_context=None):
        """ Cast ConnexionResponse to framework response class """
        return cls._build_response(
            mimetype=response.mimetype or mimetype,
            status_code=response.status_code,
            content_type=response.content_type,
            headers=response.headers,
            data=response.body,
            extra_context=extra_context,
        )

    @classmethod
    def _build_response(
        cls,
        data,
        mimetype,
        content_type=None,
        headers=None,
        status_code=None,
        extra_context=None,
    ):
        if cls._is_framework_response(data):
            raise TypeError(
                "Cannot return starlette.responses.Response in tuple. Only raw data can be returned in tuple."
            )
        data, status_code, serialized_mimetype = cls._prepare_body_and_status_code(
            data=data,
            mimetype=mimetype,
            status_code=status_code,
            extra_context=extra_context,
        )

        content_type = content_type or mimetype or serialized_mimetype

        if content_type is None:
            if isinstance(data, str):
                content_type = "text/plain"
            elif isinstance(data, bytes):
                content_type = "application/octet-stream"

        return Response(
            content=data,
            status_code=status_code,
            media_type=content_type,
            headers=headers,
        )

    @classmethod
    def _set_jsonifier(cls):
        cls.jsonifier = Jsonifier(cls=JSONEncoder)
