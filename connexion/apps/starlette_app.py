"""
This module defines an AioHttpApp, a Connexion application to wrap an AioHttp application.
"""

from connexion.apis.aiohttp_api import AioHttpApi
from http import HTTPStatus
import logging
import pathlib
import pkgutil
import sys
import asyncio
import traceback
from contextlib import suppress

from werkzeug.exceptions import HTTPException as werkzeug_HTTPException
from starlette.responses import Response
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from ..problem import problem
from ..apis.starlette_api import StarletteApi
from ..exceptions import ConnexionException, ProblemException
from .abstract import AbstractApp


logger = logging.getLogger('connexion.starlette_app')


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



class ConnexionStarletteErrorMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        sent_data = False
        async def _send(msg):
            nonlocal sent_data
            if msg["type"] == "http.response.start":
                sent_data = True
            await send(msg)
    
        try:
            await self.app(scope, receive, _send)
        except Exception as e:
            print(e)
            if sent_data:
                raise
            response = await self.handle_exception(e)
            await response(scope, receive, send)

    async def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, ProblemException):
            response = problem(status=exc.status, detail=exc.detail, title=exc.title,
                               type=exc.type, instance=exc.instance, headers=exc.headers, ext=exc.ext)
        elif isinstance(exc, werkzeug_HTTPException):
            response = problem(status=exc.code, title=exc.name, detail=exc.description)
        elif isinstance(exc, HTTPException):
            # Convert Starlette error messages to the error messages Connexion expects
            _exc = HTTPStatus(exc.status_code)
            response = problem(status=exc.status_code, title=_exc.name, detail=_exc.description)
        elif isinstance(exc, asyncio.TimeoutError):
            logger.debug('Request handler timed out.', exc_info=exc)
            response = _generic_problem(HTTPStatus.GATEWAY_TIMEOUT, exc)
        else:
            logger.exception('Error handling request', exc_info=exc)
            response = _generic_problem(HTTPStatus.INTERNAL_SERVER_ERROR, exc)

        return await StarletteApi.get_response(response)



async def _handle_httpexception(_request, exc: HTTPException):
    _exc = HTTPStatus(exc.status_code)
    response = _generic_problem(_exc)
    return await StarletteApi.get_response(response)


class StarletteApp(AbstractApp):

    def __init__(self, import_name, only_one_api=False, **kwargs):
        super().__init__(import_name, StarletteApi, server='uvicorn', **kwargs)
        self._only_one_api = only_one_api
        self._api_added = False

    def create_app(self):
        options = self.options.as_dict()

        middlewares = [Middleware(ConnexionStarletteErrorMiddleware)]
        middlewares.extend(options.get("middlewares", []))

        exception_handlers = {
            HTTPException: _handle_httpexception
        }

        return Starlette(
            **self.server_args,
            exception_handlers=exception_handlers, 
            middleware=middlewares
        )

    def get_root_path(self):
        mod = sys.modules.get(self.import_name)
        if mod is not None and hasattr(mod, '__file__'):
            return pathlib.Path(mod.__file__).resolve().parent

        loader = pkgutil.get_loader(self.import_name)
        filepath = None

        if hasattr(loader, 'get_filename'):
            filepath = loader.get_filename(self.import_name)

        if filepath is None:
            raise RuntimeError(f"Invalid import name '{self.import_name}'")

        return pathlib.Path(filepath).resolve().parent

    def set_errors_handlers(self):
        pass

    def add_api(self, specification, **kwargs):
        if self._only_one_api:
            if self._api_added:
                raise ConnexionException(
                    "an api was already added, "
                    "create a new app with 'only_one_api=False' "
                    "to add more than one api"
                )
            else:
                self.app = self._get_api(specification, kwargs).subapp
                self._api_added = True
                return self.app

        api = self._get_api(specification, kwargs)
        self.app.router.mount(api.base_path, app=api.subapp)
        return api

    def _get_api(self, specification, kwargs):
        return super().add_api(specification, **kwargs)

    def run(self, port=None, server=None, debug=None, host=None, **options):
        if port is not None:
            self.port = port
        elif self.port is None:
            self.port = 5000

        self.server = server or self.server
        self.host = host or self.host or '0.0.0.0'

        if debug is not None:
            self.debug = debug

        logger.debug('Starting %s HTTP server..', self.server, extra=vars(self))

        if self.server == 'uvicorn':
            try:
                import uvicorn
            except ImportError:
                raise Exception("uvicorn server not installed")

            logger.info('Listening on %s:%s..', self.host, self.port)
            # TODO: access log
            uvicorn.run(
                self.app, 
                host=self.host,
                port=self.port,
            )
            # access_log = options.pop('access_log', None)

            #if options.pop('use_default_access_log', None):
            #    access_log = logger

            #web.run_app(self.app, port=self.port, host=self.host, access_log=access_log, **options)
        else:
            raise Exception(f'Server {self.server} not recognized')


    async def __call__(self, scope, receive, send):
        return await self.app(scope, receive, send)
