"""
This module defines a FlaskApp, a Connexion application to wrap a Flask application.
"""

import logging
import pathlib
from types import FunctionType  # NOQA

import a2wsgi
import flask
import werkzeug.exceptions
from flask import signals

from connexion import jsonifier
from connexion.apis.flask_api import FlaskApi
from connexion.apps.abstract import AbstractApp
from connexion.exceptions import ProblemException
from connexion.middleware import ConnexionMiddleware
from connexion.middleware.wsgi import WSGIMiddleware
from connexion.problem import problem

logger = logging.getLogger("connexion.app")


class FlaskApp(AbstractApp):
    def __init__(
        self, import_name, server="flask", server_args=None, extra_files=None, **kwargs
    ):
        """
        :param extra_files: additional files to be watched by the reloader, defaults to the swagger specs of added apis
        :type extra_files: list[str | pathlib.Path], optional

        See :class:`~connexion.AbstractApp` for additional parameters.
        """
        self.import_name = import_name

        self.server = server
        self.server_args = dict() if server_args is None else server_args
        self.extra_files = extra_files or []

        self.app = self.create_app()

        super().__init__(import_name, FlaskApi, **kwargs)

    def create_app(self):
        app = flask.Flask(self.import_name, **self.server_args)
        app.json = FlaskJSONProvider(app)
        app.url_map.converters["float"] = NumberConverter
        app.url_map.converters["int"] = IntegerConverter
        return app

    def _apply_middleware(self, middlewares):
        middlewares = [*middlewares, WSGIMiddleware]
        middleware = ConnexionMiddleware(self.app.wsgi_app, middlewares=middlewares)

        # Wrap with ASGI to WSGI middleware for usage with development server and test client
        self.app.wsgi_app = a2wsgi.ASGIMiddleware(middleware)

        return middleware

    def get_root_path(self):
        return pathlib.Path(self.app.root_path)

    def set_errors_handlers(self):
        for error_code in werkzeug.exceptions.default_exceptions:
            self.add_error_handler(error_code, self.common_error_handler)

        self.add_error_handler(ProblemException, self.common_error_handler)

    def common_error_handler(self, exception):
        """
        :type exception: Exception
        """
        if isinstance(exception, ProblemException):
            response = problem(
                status=exception.status,
                title=exception.title,
                detail=exception.detail,
                type=exception.type,
                instance=exception.instance,
                headers=exception.headers,
                ext=exception.ext,
            )
        else:
            if not isinstance(exception, werkzeug.exceptions.HTTPException):
                exception = werkzeug.exceptions.InternalServerError()

            response = problem(
                title=exception.name,
                detail=exception.description,
                status=exception.code,
                headers=exception.get_headers(),
            )

        if response.status_code >= 500:
            signals.got_request_exception.send(self.app, exception=exception)

        return FlaskApi.get_response(response)

    def add_api(self, specification, **kwargs):
        api = super().add_api(specification, **kwargs)
        self.app.register_blueprint(api.blueprint)
        if isinstance(specification, (str, pathlib.Path)):
            self.extra_files.append(self.specification_dir / specification)
        return api

    def add_error_handler(self, error_code, function):
        # type: (int, FunctionType) -> None
        self.app.register_error_handler(error_code, function)

    def route(self, rule: str, **kwargs):
        """
        A decorator that is used to register a view function for a
        given URL rule.  This does the same thing as `add_url_rule`
        but is intended for decorator usage::

            @app.route('/')
            def index():
                return 'Hello World'

        :param rule: the URL rule as string
        :param kwargs: kwargs to be forwarded to the underlying `werkzeug.routing.Rule` object.
        """
        logger.debug("Adding %s with decorator", rule, extra=kwargs)
        return self.app.route(rule, **kwargs)

    def run(
        self, port=None, server=None, debug=None, host=None, extra_files=None, **options
    ):  # pragma: no cover
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
        :param extra_files: additional files to be watched by the reloader.
        :type extra_files: Iterable[str | pathlib.Path]
        :param options: options to be forwarded to the underlying server
        """
        # this functions is not covered in unit tests because we would effectively testing the mocks

        # overwrite constructor parameter
        if port is not None:
            self.port = port
        elif self.port is None:
            self.port = 5000

        self.host = host or self.host or "0.0.0.0"

        if server is not None:
            self.server = server

        if debug is not None:
            self.debug = debug

        if extra_files is not None:
            self.extra_files.extend(extra_files)

        logger.debug("Starting %s HTTP server..", self.server, extra=vars(self))
        if self.server == "flask":
            self.app.run(
                self.host,
                port=self.port,
                debug=self.debug,
                extra_files=self.extra_files,
                **options,
            )
        elif self.server == "tornado":
            try:
                import tornado.autoreload
                import tornado.httpserver
                import tornado.ioloop
                import tornado.wsgi
            except ImportError:
                raise Exception("tornado library not installed")
            wsgi_container = tornado.wsgi.WSGIContainer(self.app)
            http_server = tornado.httpserver.HTTPServer(wsgi_container, **options)
            http_server.listen(self.port, address=self.host)
            if self.debug:
                tornado.autoreload.start()
            logger.info("Listening on %s:%s..", self.host, self.port)
            tornado.ioloop.IOLoop.instance().start()
        elif self.server == "gevent":
            try:
                import gevent.pywsgi
            except ImportError:
                raise Exception("gevent library not installed")
            if self.debug:
                logger.warning(
                    "gevent server doesn't support debug mode. Please switch to flask/tornado server."
                )
            http_server = gevent.pywsgi.WSGIServer(
                (self.host, self.port), self.app, **options
            )
            logger.info("Listening on %s:%s..", self.host, self.port)
            http_server.serve_forever()
        else:
            raise Exception(f"Server {self.server} not recognized")

    def __call__(self, scope, receive, send):
        """
        ASGI interface. Calls the middleware wrapped around the wsgi app.
        """
        return self.middleware(scope, receive, send)


class FlaskJSONProvider(flask.json.provider.DefaultJSONProvider):
    """Custom JSONProvider which adds connexion defaults on top of Flask's"""

    @jsonifier.wrap_default
    def default(self, o):
        return super().default(o)


class NumberConverter(werkzeug.routing.BaseConverter):
    """Flask converter for OpenAPI number type"""

    regex = r"[+-]?[0-9]*(\.[0-9]*)?"

    def to_python(self, value):
        return float(value)


class IntegerConverter(werkzeug.routing.BaseConverter):
    """Flask converter for OpenAPI integer type"""

    regex = r"[+-]?[0-9]+"

    def to_python(self, value):
        return int(value)
