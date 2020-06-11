import datetime
import logging
import pathlib
from decimal import Decimal
from types import FunctionType  # NOQA

import sanic
from sanic import Sanic
from sanic.exceptions import SanicException, ServerError, NotFound
from sanic.response import json

from ..apis.sanic_api import SanicApi
from ..exceptions import ProblemException
from ..problem import problem
from .abstract import AbstractApp

logger = logging.getLogger('connexion.app')


class SanicApp(AbstractApp):
    def __init__(self, import_name, server='sanic', **kwargs):
        super(SanicApp, self).__init__(import_name, SanicApi, server=server, **kwargs)

    def create_app(self):
        app = Sanic(self.import_name, **self.server_args)
        return app

    def get_root_path(self):
        self.app.root_path = "./"
        return pathlib.Path(self.app.root_path)

    def set_errors_handlers(self):
        for error_code in sanic.exceptions._sanic_exceptions.values():
            self.add_error_handler(error_code, self.common_error_handler)

        self.add_error_handler(ProblemException, self.common_error_handler)

    @staticmethod
    async def common_error_handler(request, exception):
        """
        :type exception: Exception
        """
        if isinstance(exception, ProblemException):
            response = problem(
                status=exception.status, title=exception.title, detail=exception.detail,
                type=exception.type, instance=exception.instance, headers=exception.headers,
                ext=exception.ext)
        else:
            if not isinstance(exception, SanicException):
                exception = ServerError()

            response = problem(title=exception.__class__.__name__, detail=exception.args,
                               status=exception.status_code)
        #
        # XXX stub return json-problems
        #
        return json(status=response.status_code, body=response.body, content_type=response.content_type)
        # return SanicApi.get_response(response)

    def add_api(self, specification, **kwargs):
        api = super(SanicApp, self).add_api(specification, **kwargs)
        self.app.register_blueprint(api.blueprint)
        return api

    def add_error_handler(self, error_code, function):
        # type: (int, FunctionType) -> None

        self.app.error_handler.add(error_code, function)

    def run(self, port=None, server=None, debug=None, host=None, **options):  # pragma: no cover
        """
        Runs the application on a local development server.
        :param host: the host interface to bind on.
        :type host: str
        :param port: port to listen to
        :type port: int
        :param server: which wsgi server to use
        :type server: str | None
        :param debug: include debugging information
        :type debug: bool
        :param options: options to be forwarded to the underlying server
        """
        # this functions is not covered in unit tests because we would effectively testing the mocks

        # overwrite constructor parameter
        if port is not None:
            self.port = port
        elif self.port is None:
            self.port = 5000

        self.host = host or self.host or '0.0.0.0'

        if server is not None:
            self.server = server

        if debug is not None:
            self.debug = debug

        logger.debug('Starting %s HTTP server..', self.server, extra=vars(self))
        if self.server == 'sanic':
            self.app.run(self.host, port=self.port, debug=self.debug, **options)
        else:
            raise Exception('Server {} not recognized'.format(self.server))
