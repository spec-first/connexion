import asyncio
import logging
import re
import traceback
from contextlib import suppress
from http import HTTPStatus
from re import findall
from urllib.parse import parse_qs

import aiohttp_jinja2
import sanic
from sanic import Blueprint
from sanic.exceptions import NotFound as HTTPNotFound
from sanic.request import Request
from sanic.response import HTTPResponse, json, redirect, text

from connexion.apis.abstract import AbstractAPI
from connexion.exceptions import ProblemException
from connexion.handlers import AuthErrorHandler
from connexion.jsonifier import JSONEncoder, Jsonifier
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.problem import problem
from connexion.utils import yamldumper

from .flask_utils import flaskify_endpoint

logger = logging.getLogger("connexion.apis.sanic_api")


def _generic_problem(http_status: HTTPStatus, exc: Exception = None):
    extra = None
    if exc is not None:
        loop = asyncio.get_event_loop()
        if loop.get_debug():
            tb = None
            with suppress(Exception):
                tb = traceback.format_exc()
            if tb:
                extra = {"traceback": tb}

    return problem(
        status=http_status.value,
        title=http_status.phrase,
        detail=http_status.description,
        ext=extra,
    )


def replace_braces(path, parameters):
    schemed_parameters = {
        p["name"]: p["schema"]
        for p in parameters
        if p.get("in") == "path"
        and p.get("schema", {}).get("type") in ("string", "integer", "number")
    }
    for p_name in findall(r"{([a-zA-Z\_]+)}", path):
        src = f"{{{p_name}}}"
        p_scheme = ""

        if p_name in schemed_parameters:
            p_type = schemed_parameters[p_name]["type"]
            if p_type in ("integer",):
                p_scheme = ":int"
            elif p_type in ("number",):
                p_scheme = ":number"
            elif p_type in ("string",):
                if schemed_parameters[p_name].get("pattern"):
                    p_scheme = ":" + schemed_parameters[p_name].get("pattern").strip()
                else:
                    p_scheme = ":string"

        dest = f"<{p_name}{p_scheme}>"
        path = path.replace(src, dest)

    return path


class SanicApi(AbstractAPI):
    def __init__(self, *args, **kwargs):
        AbstractAPI.__init__(self, *args, **kwargs)

    def _set_base_path(self, base_path):
        AbstractAPI._set_base_path(self, base_path)
        self._api_name = SanicApi.normalize_string(self.base_path)
        logger.debug("Creating API blueprint: %s", self.base_path)
        endpoint = flaskify_endpoint(self.base_path)
        self.blueprint = Blueprint(endpoint, url_prefix=self.base_path)

    @staticmethod
    def normalize_string(string):
        return re.sub(r"[^a-zA-Z0-9]", "_", string.strip("/"))

    def _base_path_for_prefix(self, request):
        """
        returns a modified basePath which includes the incoming request's
        path prefix.
        """
        base_path = self.base_path
        if not request.path.startswith(self.base_path):
            prefix = request.path.split(self.base_path)[0]
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

        async def _get_openapi_json(request):
            return HTTPResponse(
                status=200,
                content_type="application/json",
                body=self.jsonifier.dumps(self._spec_for_prefix(request)),
            )

        self.blueprint.add_route(
            methods=["GET"],
            uri=self.options.openapi_spec_path,
            handler=_get_openapi_json,
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

        async def _get_openapi_yaml(request):
            return HTTPResponse(
                status=200,
                content_type="text/yaml",
                body=yamldumper(self._spec_for_prefix(request)),
            )

        self.blueprint.add_route(
            methods=["GET"], uri=openapi_spec_path_yaml, handler=_get_openapi_yaml
        )

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_path}/ui/
        """
        console_ui_path = self.options.openapi_console_ui_path.strip().rstrip("/")
        logger.debug("Adding swagger-ui: %s%s/", self.base_path, console_ui_path)
        from swagger_ui_bundle import swagger_ui_path
        from pathlib import Path

        swagger_ui_localpath = Path(swagger_ui_path)

        async def _get_swagger_ui_config(req):
            return HTTPResponse(
                status=200,
                content_type="text/json",
                body=self.jsonifier.dumps(self.options.openapi_console_ui_config),
            )

        async def _get_swagger_ui_home(req):
            import jinja2

            template_str = (swagger_ui_localpath / "index.j2").read_text()
            t = jinja2.Template(template_str)
            base_path = self._base_path_for_prefix(req)
            template_variables = {
                "openapi_spec_url": (base_path + self.options.openapi_spec_path)
            }
            if self.options.openapi_console_ui_config is not None:
                template_variables["configUrl"] = "swagger-ui-config.json"
            return text(t.render(template_variables), content_type="text/html")

        for path in (
            console_ui_path + "/",
            console_ui_path + "/index.html",
        ):
            self.blueprint.add_route(
                methods=["GET"], uri=path, handler=_get_swagger_ui_home
            )

        if self.options.openapi_console_ui_config is not None:
            self.blueprint.add_route(
                methods=["GET"],
                uri=console_ui_path + "/swagger-ui-config.json",
                handler=_get_swagger_ui_config,
            )

        for f in (
            "swagger-ui.css",
            "swagger-ui-bundle.js",
            "swagger-ui-standalone-preset.js",
        ):
            p = swagger_ui_localpath / f
            self.blueprint.static(console_ui_path + "/" + f, str(p.absolute()))
        # we have to add an explicit redirect instead of relying on the
        # normalize_path_middleware because we also serve static files
        # from this dir (below)

        async def _redirect(request):
            return redirect(to=self.base_path + console_ui_path + "/")

        if False:
            self.blueprint.add_route(
                methods=["GET"], uri=console_ui_path, handler=_redirect
            )

        if False:
            # this route will match and get a permission error when trying to
            # serve index.html, so we add the redirect above.
            self.blueprint.static(
                console_ui_path,
                str(self.options.openapi_console_ui_from_dir),
                name="swagger_ui_static",
            )

    def add_auth_on_not_found(self, security, security_definitions):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug("Adding path not found authentication")
        not_found_error = AuthErrorHandler(
            self,
            _HttpNotFoundError(),
            security=security,
            security_definitions=security_definitions,
        )
        endpoint_name = "{}_not_found".format(self._api_name)
        self.blueprint.add_route(
            methods=["*"],
            uri="/{not_found_path}",
            handler=not_found_error.function,
            name=endpoint_name,
        )

    def _add_operation_internal(self, method, path, operation):
        method = method.upper()
        operation_id = operation.operation_id or path

        logger.debug("... Adding %s -> %s", method, operation_id, extra=vars(operation))

        handler = operation.function
        endpoint_name = "{}_{}_{}".format(
            self._api_name, SanicApi.normalize_string(path), method.lower()
        )
        sanic_path = replace_braces(path, operation.parameters)
        logger.debug("... Replace %r -> %r", path, sanic_path)
        self.blueprint.add_route(
            methods=[method], uri=sanic_path, handler=handler, name=endpoint_name
        )

    @classmethod
    async def get_request(cls, req: Request, *args, **kwargs):
        """Convert Sanic request to connexion

        :param req: instance of sanic.request.Request
        :return: connexion request instance
        :rtype: ConnexionRequest
        """
        context_dict = {"request": req}  # XXX: fixme use aiohttp-context with sanic
        url = str(req.url)
        has_body = bool(req.body)
        logger.debug(
            "Getting data and status code", extra={"has_body": has_body, "url": url}
        )

        query = dict(req.query_args)
        headers = req.headers
        body = None
        if has_body:
            body = req.body  # AWAIT FIXME

        return ConnexionRequest(
            url=url,
            method=req.method.lower(),
            path_params=dict(req.match_info),
            query=query,
            headers=headers,
            body=body,
            json_getter=lambda: cls.jsonifier.loads(body),
            files={},
            context=context_dict,
        )

    @classmethod
    async def get_response(cls, response: HTTPResponse, mimetype=None, request=None):
        """Get response.
        This method is used in the lifecycle decorators

        :type response: aiohttp.web.StreamResponse | (Any,) | (Any, int) | (Any, dict) | (Any, int, dict)
        :rtype: aiohttp.web.Response
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
        return isinstance(response, sanic.response.HTTPResponse)

    @classmethod
    def _framework_to_connexion_response(cls, response, mimetype):
        """ Cast framework response class to ConnexionResponse used for schema validation """
        body = None
        if hasattr(response, "body"):  # StreamResponse and FileResponse don't have body
            body = response.body
        return ConnexionResponse(
            status_code=response.status,
            mimetype=mimetype,
            content_type=response.content_type,
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
                "Cannot return web.StreamResponse in tuple. Only raw data can be returned in tuple."
            )

        # import pdb; pdb.set_trace()
        data, status_code, serialized_mimetype = cls._prepare_body_and_status_code(
            data=data,
            mimetype=mimetype,
            status_code=status_code,
            extra_context=extra_context,
        )

        body = data.encode() if isinstance(data, str) else data

        content_type = content_type or mimetype or serialized_mimetype
        return HTTPResponse(
            body=body, headers=headers, status=status_code, content_type=content_type
        )

    @classmethod
    def _set_jsonifier(cls):
        cls.jsonifier = Jsonifier(cls=JSONEncoder)


class _HttpNotFoundError(HTTPNotFound):
    def __init__(self):

        self.name = "Not Found"
        self.description = (
            "The requested URL was not found on the server. "
            "If you entered the URL manually please check your spelling and "
            "try again."
        )
        self.code = type(self).status_code
        self.empty_body = True

        HTTPNotFound.__init__(self, message=self.name)
