"""
This module defines an AioHttpApp, a Connexion application to wrap an AioHttp application.
"""

import logging
import pathlib
import pkgutil
import sys

from starlette.applications import Starlette

from ..apis.starlette_api import StarletteApi
from ..exceptions import ConnexionException
from .abstract import AbstractApp

logger = logging.getLogger('connexion.aiohttp_app')


class StarletteApp(AbstractApp):

    def __init__(self, import_name, only_one_api=False, **kwargs):
        super().__init__(import_name, StarletteApi, server='uvicorn', **kwargs)
        self._only_one_api = only_one_api
        self._api_added = False

    def create_app(self):
        return Starlette(**self.server_args)

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
            print(self.app.routes) 
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
