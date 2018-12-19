import asyncio
import logging
import os.path
import pkgutil
import sys

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from ..apis.aiohttp_api import AioHttpApi
from ..exceptions import ConnexionException
from ..lifecycle import ConnexionResponse
from ..tests import AbstractClient
from ..utils import is_json_mimetype
from .abstract import AbstractApp

logger = logging.getLogger('connexion.aiohttp_app')


class AioHttpApp(AbstractApp):

    api_cls = AioHttpApi

    def __init__(self, import_name, only_one_api=False, **kwargs):
        super(AioHttpApp, self).__init__(import_name, self.api_cls, server='aiohttp', **kwargs)
        self._only_one_api = only_one_api
        self._api_added = False

    def create_app(self):
        return web.Application(debug=self.debug)

    def get_root_path(self):
        mod = sys.modules.get(self.import_name)
        if mod is not None and hasattr(mod, '__file__'):
            return os.path.dirname(os.path.abspath(mod.__file__))

        loader = pkgutil.get_loader(self.import_name)
        filepath = None

        if hasattr(loader, 'get_filename'):
            filepath = loader.get_filename(self.import_name)

        if filepath is None:
            raise RuntimeError("Invalid import name '{}'".format(self.import_name))

        return os.path.dirname(os.path.abspath(filepath))

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
        try:
            self.app.add_subapp(api.base_path, api.subapp)
        except ValueError:
            raise ConnexionException(
                "aiohttp doesn't allow to set empty base_path ('/'), "
                "use non-empty instead, e.g /api"
            )

        return api

    def _get_api(self, specification, kwargs):
        return super(AioHttpApp, self).add_api(specification, **kwargs)

    def run(self, port=None, server=None, debug=None, host=None, **options):
        if port is not None:
            self.port = port
        elif self.port is None:
            self.port = 5000

        self.server = server or self.server
        self.host = host or self.host or '0.0.0.0'

        if debug is not None:
            self.debug = debug
            self.app._debug = debug
            for subapp in self.app._subapps:
                subapp._debug = debug

        logger.debug('Starting %s HTTP server..', self.server, extra=vars(self))

        if self.server == 'aiohttp':
            logger.info('Listening on %s:%s..', self.host, self.port)

            access_log = options.get('access_log')

            if options.get('use_default_access_log'):
                access_log = logger

            web.run_app(self.app, port=self.port, host=self.host, access_log=access_log)
        else:
            raise Exception('Server {} not recognized'.format(self.server))

    def test_client(self):
        """Return a flask's test_client compatible."""
        return AioHttpClient.from_app(self)


class AioHttpClient(AbstractClient):
    """ A specific test client for aiohttp framework."""

    def _request(
        self,
        method,
        url,
        **kwargs
    ):
        # code inspired from https://github.com/aio-libs/aiohttp/blob/v3.4.4/aiohttp/pytest_plugin.py#L286
        # set the loop in the app,
        # and use only this one to avoid loop conflicts
        self.app.app._set_loop(None)
        loop = self.app.app.loop
        client = TestClient(TestServer(self.app.app, loop=loop), loop=loop)
        loop.run_until_complete(client.start_server())

        @asyncio.coroutine
        def _async_request():
            nonlocal client
            content_type = kwargs.get("content_type")
            if content_type:
                headers = kwargs.setdefault("headers", {})
                if "Content-Type" not in headers:
                    headers["Content-Type"] = content_type
            kwargs["params"] = kwargs.get("query_string")
            res = yield from client.request(method.upper(), url, **kwargs)
            body = yield from res.read()
            return ConnexionResponse(
                status_code=res.status,
                headers=res.headers,
                body=body
            )

        response = loop.run_until_complete(_async_request())
        loop.run_until_complete(client.close())
        return response
