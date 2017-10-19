import logging
import os.path
import pkgutil
import sys

from aiohttp import web

from ..apis.aiohttp_api import AioHttpApi
from .abstract import AbstractApp

logger = logging.getLogger('connexion.aiohttp_app')


class AioHttpApp(AbstractApp):

    def __init__(self, import_name, **kwargs):
        super(AioHttpApp, self).__init__(import_name, AioHttpApi, server='aiohttp', **kwargs)

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
        api = super(AioHttpApp, self).add_api(specification, **kwargs)
        self.app.add_subapp(api.base_path, api.aiohttp_api)
        return api

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
