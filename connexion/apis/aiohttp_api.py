import asyncio
import logging
import re
import traceback
from contextlib import suppress
from http import HTTPStatus
from urllib.parse import parse_qs

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPPermanentRedirect
from aiohttp.web_middlewares import normalize_path_middleware
from connexion.apis.abstract import AbstractAPI
from connexion.exceptions import ProblemException
from connexion.handlers import AuthErrorHandler
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.problem import problem
from connexion.utils import Jsonifier, is_json_mimetype, yamldumper
from werkzeug.exceptions import HTTPException as werkzeug_HTTPException

try:
    import ujson as json
    from functools import partial
    json.dumps = partial(json.dumps, escape_forward_slashes=True)

except ImportError:  # pragma: no cover
    import json

logger = logging.getLogger('connexion.apis.aiohttp_api')


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


@web.middleware
@asyncio.coroutine
def problems_middleware(request, handler):
    try:
        response = yield from handler(request)
    except ProblemException as exc:
        response = exc.to_problem()
    except (werkzeug_HTTPException, _HttpNotFoundError) as exc:
        response = problem(status=exc.code, title=exc.name, detail=exc.description)
    except web.HTTPError as exc:
        if exc.text == "{}: {}".format(exc.status, exc.reason):
            detail = HTTPStatus(exc.status).description
        else:
            detail = exc.text
        response = problem(status=exc.status, title=exc.reason, detail=detail)
    except (
        web.HTTPException,  # eg raised HTTPRedirection or HTTPSuccessful
        asyncio.CancelledError,  # skipped in default web_protocol
    ):
        # leave this to default handling in aiohttp.web_protocol.RequestHandler.start()
        raise
    except asyncio.TimeoutError as exc:
        # overrides 504 from aiohttp.web_protocol.RequestHandler.start()
        logger.debug('Request handler timed out.', exc_info=exc)
        response = _generic_problem(HTTPStatus.GATEWAY_TIMEOUT, exc)
    except Exception as exc:
        # overrides 500 from aiohttp.web_protocol.RequestHandler.start()
        logger.exception('Error handling request', exc_info=exc)
        response = _generic_problem(HTTPStatus.INTERNAL_SERVER_ERROR, exc)

    if isinstance(response, ConnexionResponse):
        response = yield from AioHttpApi.get_response(response)
    return response


class AioHttpApi(AbstractAPI):
    def __init__(self, *args, **kwargs):
        # NOTE we use HTTPPermanentRedirect (308) because
        # clients sometimes turn POST requests into GET requests
        # on 301, 302, or 303
        # see https://tools.ietf.org/html/rfc7538
        trailing_slash_redirect = normalize_path_middleware(
            append_slash=True,
            redirect_class=HTTPPermanentRedirect
        )
        self.subapp = web.Application(
            middlewares=[
                problems_middleware,
                trailing_slash_redirect
            ]
        )
        AbstractAPI.__init__(self, *args, **kwargs)

        aiohttp_jinja2.setup(
            self.subapp,
            loader=jinja2.FileSystemLoader(
                str(self.options.openapi_console_ui_from_dir)
            )
        )
        middlewares = self.options.as_dict().get('middlewares', [])
        self.subapp.middlewares.extend(middlewares)

    def _set_base_path(self, base_path):
        AbstractAPI._set_base_path(self, base_path)
        self._api_name = AioHttpApi.normalize_string(self.base_path)

    @staticmethod
    def normalize_string(string):
        return re.sub(r'[^a-zA-Z0-9]', '_', string.strip('/'))

    def add_openapi_json(self):
        """
        Adds openapi json to {base_path}/openapi.json
             (or {base_path}/swagger.json for swagger2)
        """
        logger.debug('Adding spec json: %s/%s', self.base_path,
                     self.options.openapi_spec_path)
        self.subapp.router.add_route(
            'GET',
            self.options.openapi_spec_path,
            self._get_openapi_json
        )

    def add_openapi_yaml(self):
        """
        Adds openapi json to {base_path}/openapi.json
             (or {base_path}/swagger.json for swagger2)
        """
        if not self.options.openapi_spec_path.endswith("json"):
            return

        openapi_spec_path_yaml = self.options.openapi_spec_path[:-len("json")] + "yaml"
        logger.debug('Adding spec yaml: %s/%s', self.base_path,
                     openapi_spec_path_yaml)
        self.subapp.router.add_route(
            'GET',
            openapi_spec_path_yaml,
            self._get_openapi_yaml
        )

    @asyncio.coroutine
    def _get_openapi_json(self, req):
        return web.Response(
            status=200,
            content_type='application/json',
            body=self.jsonifier.dumps(self.specification.raw)
        )

    @asyncio.coroutine
    def _get_openapi_yaml(self, req):
        return web.Response(
            status=200,
            content_type='text/yaml',
            body=yamldumper(self.specification.raw)
        )

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_path}/ui/
        """
        console_ui_path = self.options.openapi_console_ui_path.strip().rstrip('/')
        logger.debug('Adding swagger-ui: %s%s/',
                     self.base_path,
                     console_ui_path)

        for path in (
            console_ui_path + '/',
            console_ui_path + '/index.html',
        ):
            self.subapp.router.add_route(
                'GET',
                path,
                self._get_swagger_ui_home
            )

        # we have to add an explicit redirect instead of relying on the
        # normalize_path_middleware because we also serve static files
        # from this dir (below)

        @asyncio.coroutine
        def redirect(request):
            raise web.HTTPMovedPermanently(
                location=self.base_path + console_ui_path + '/'
            )

        self.subapp.router.add_route(
            'GET',
            console_ui_path,
            redirect
        )

        # this route will match and get a permission error when trying to
        # serve index.html, so we add the redirect above.
        self.subapp.router.add_static(
            console_ui_path,
            path=str(self.options.openapi_console_ui_from_dir),
            name='swagger_ui_static'
        )

    @aiohttp_jinja2.template('index.j2')
    @asyncio.coroutine
    def _get_swagger_ui_home(self, req):
        return {'openapi_spec_url': (self.base_path +
                                     self.options.openapi_spec_path)}

    def add_auth_on_not_found(self, security, security_definitions):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug('Adding path not found authentication')
        not_found_error = AuthErrorHandler(
            self, _HttpNotFoundError(),
            security=security,
            security_definitions=security_definitions
        )
        endpoint_name = "{}_not_found".format(self._api_name)
        self.subapp.router.add_route(
            '*',
            '/{not_found_path}',
            not_found_error.function,
            name=endpoint_name
        )

    def _add_operation_internal(self, method, path, operation):
        method = method.upper()
        operation_id = operation.operation_id or path

        logger.debug('... Adding %s -> %s', method, operation_id,
                     extra=vars(operation))

        handler = operation.function
        endpoint_name = '{}_{}_{}'.format(
            self._api_name,
            AioHttpApi.normalize_string(path),
            method.lower()
        )
        self.subapp.router.add_route(
            method, path, handler, name=endpoint_name
        )

        if not path.endswith('/'):
            self.subapp.router.add_route(
                method, path + '/', handler, name=endpoint_name + '_'
            )

    @classmethod
    @asyncio.coroutine
    def get_request(cls, req):
        """Convert aiohttp request to connexion

        :param req: instance of aiohttp.web.Request
        :return: connexion request instance
        :rtype: ConnexionRequest
        """
        url = str(req.url)
        logger.debug('Getting data and status code',
                     extra={'has_body': req.has_body, 'url': url})

        query = parse_qs(req.rel_url.query_string)
        headers = req.headers
        body = None
        if req.body_exists:
            body = yield from req.read()

        return ConnexionRequest(url=url,
                                method=req.method.lower(),
                                path_params=dict(req.match_info),
                                query=query,
                                headers=headers,
                                body=body,
                                json_getter=lambda: cls.jsonifier.loads(body),
                                files={},
                                context=req)

    @classmethod
    @asyncio.coroutine
    def get_response(cls, response, mimetype=None, request=None):
        """Get response.
        This method is used in the lifecycle decorators

        :rtype: aiohttp.web.Response
        """
        while asyncio.iscoroutine(response):
            response = yield from response

        url = str(request.url) if request else ''

        logger.debug('Getting data and status code',
                     extra={
                         'data': response,
                         'url': url
                     })

        if isinstance(response, ConnexionResponse):
            response = cls._get_aiohttp_response_from_connexion(response, mimetype)

        if isinstance(response, web.StreamResponse):
            logger.debug('Got stream response with status code (%d)',
                         response.status, extra={'url': url})
        else:
            logger.debug('Got data and status code (%d)',
                         response.status, extra={'data': response.body, 'url': url})

        return response

    @classmethod
    def get_connexion_response(cls, response, mimetype=None):
        response.body = cls._cast_body(response.body, mimetype)

        if isinstance(response, ConnexionResponse):
            return response

        return ConnexionResponse(
            status_code=response.status,
            mimetype=response.content_type,
            content_type=response.content_type,
            headers=response.headers,
            body=response.body
        )

    @classmethod
    def _get_aiohttp_response_from_connexion(cls, response, mimetype):
        content_type = response.content_type if response.content_type else \
            response.mimetype if response.mimetype else mimetype

        body = cls._cast_body(response.body, content_type)

        return web.Response(
            status=response.status_code,
            content_type=content_type,
            headers=response.headers,
            body=body
        )

    @classmethod
    def _cast_body(cls, body, content_type=None):
        if not isinstance(body, bytes):
            if content_type and is_json_mimetype(content_type):
                return json.dumps(body).encode()

            elif isinstance(body, str):
                return body.encode()

            else:
                return str(body).encode()
        else:
            return body

    @classmethod
    def _set_jsonifier(cls):
        cls.jsonifier = Jsonifier(json)


class _HttpNotFoundError(HTTPNotFound):
    def __init__(self):
        self.name = 'Not Found'
        self.description = (
            'The requested URL was not found on the server. '
            'If you entered the URL manually please check your spelling and '
            'try again.'
        )
        self.code = type(self).status_code
        self.empty_body = True

        HTTPNotFound.__init__(self, reason=self.name)
