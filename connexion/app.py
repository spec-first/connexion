"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import logging
import pathlib
import flask
import werkzeug.exceptions
from .problem import problem
from .api import Api
from connexion.resolver import Resolver

logger = logging.getLogger('connexion.app')


class App:
    def __init__(self, import_name, port=None, specification_dir='', server=None, arguments=None, auth_all_paths=False,
                 debug=False, swagger_ui=True, swagger_path=None, swagger_url=None):
        """
        :param import_name: the name of the application package
        :type import_name: str
        :param port: port to listen to
        :type port: int
        :param specification_dir: directory where to look for specifications
        :type specification_dir: pathlib.Path | str
        :param server: which wsgi server to use
        :type server: str | None
        :param arguments: arguments to replace on the specification
        :type arguments: dict | None
        :param auth_all_paths: whether to authenticate not defined paths
        :type auth_all_paths: bool
        :param debug: include debugging information
        :type debug: bool
        :param swagger_ui: whether to include swagger ui or not
        :type swagger_ui: bool
        :param swagger_path: path to swagger-ui directory
        :type swagger_path: string | None
        :param swagger_url: URL to access swagger-ui documentation
        :type swagger_url: string | None
        """
        self.app = flask.Flask(import_name)

        # we get our application root path from flask to avoid duplicating logic
        self.root_path = pathlib.Path(self.app.root_path)
        logger.debug('Root Path: %s', self.root_path)

        specification_dir = pathlib.Path(specification_dir)  # Ensure specification dir is a Path
        if specification_dir.is_absolute():
            self.specification_dir = specification_dir
        else:
            self.specification_dir = self.root_path / specification_dir

        logger.debug('Specification directory: %s', self.specification_dir)

        logger.debug('Setting error handlers')
        for error_code in range(400, 600):  # All http status from 400 to 599 are errors
            self.add_error_handler(error_code, self.common_error_handler)

        self.port = port
        self.server = server or 'flask'
        self.debug = debug
        self.import_name = import_name
        self.arguments = arguments or {}
        self.swagger_ui = swagger_ui
        self.swagger_path = swagger_path
        self.swagger_url = swagger_url
        self.auth_all_paths = auth_all_paths

    @staticmethod
    def common_error_handler(exception):
        """
        :type exception: Exception
        """
        if not isinstance(exception, werkzeug.exceptions.HTTPException):
            exception = werkzeug.exceptions.InternalServerError()
        return problem(title=exception.name, detail=exception.description, status=exception.code)

    def add_api(self, swagger_file, base_path=None, arguments=None, auth_all_paths=None, swagger_ui=None,
                swagger_path=None, swagger_url=None, validate_responses=False, resolver=Resolver()):
        """
        Adds an API to the application based on a swagger file

        :param swagger_file: swagger file with the specification
        :type swagger_file: pathlib.Path
        :param base_path: base path where to add this api
        :type base_path: str | None
        :param arguments: api version specific arguments to replace on the specification
        :type arguments: dict | None
        :param auth_all_paths: whether to authenticate not defined paths
        :type auth_all_paths: bool
        :param swagger_ui: whether to include swagger ui or not
        :type swagger_ui: bool
        :param swagger_path: path to swagger-ui directory
        :type swagger_path: string | None
        :param swagger_url: URL to access swagger-ui documentation
        :type swagger_url: string | None
        :param validate_responses: True enables validation. Validation errors generate HTTP 500 responses.
        :type validate_responses: bool
        :param resolver: Operation resolver.
        :type resolver: Resolver | types.FunctionType
        :rtype: Api
        """
        resolver = Resolver(resolver) if hasattr(resolver, '__call__') else resolver

        swagger_ui = swagger_ui if swagger_ui is not None else self.swagger_ui
        swagger_path = swagger_path if swagger_path is not None else self.swagger_path
        swagger_url = swagger_url if swagger_url is not None else self.swagger_url
        auth_all_paths = auth_all_paths if auth_all_paths is not None else self.auth_all_paths
        logger.debug('Adding API: %s', swagger_file)
        # TODO test if base_url starts with an / (if not none)
        arguments = arguments or dict()
        arguments = dict(self.arguments, **arguments)  # copy global arguments and update with api specfic
        yaml_path = self.specification_dir / swagger_file
        api = Api(swagger_yaml_path=yaml_path,
                  base_url=base_path, arguments=arguments,
                  swagger_ui=swagger_ui,
                  swagger_path=swagger_path,
                  swagger_url=swagger_url,
                  resolver=resolver,
                  validate_responses=validate_responses,
                  auth_all_paths=auth_all_paths)
        self.app.register_blueprint(api.blueprint)
        return api

    def add_error_handler(self, error_code, function):
        """

        :type error_code: int
        :type function: types.FunctionType
        """
        self.app.error_handler_spec[None][error_code] = function

    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """
        Connects a URL rule.  Works exactly like the `route` decorator.  If a view_func is provided it will be
        registered with the endpoint.

        Basically this example::

            @app.route('/')
            def index():
                pass

        Is equivalent to the following::

            def index():
                pass
            app.add_url_rule('/', 'index', index)

        If the view_func is not provided you will need to connect the endpoint to a view function like so::

            app.view_functions['index'] = index

        Internally`route` invokes `add_url_rule` so if you want to customize the behavior via subclassing you only need
        to change this method.

        :param rule: the URL rule as string
        :type rule: str
        :param endpoint: the endpoint for the registered URL rule. Flask itself assumes the name of the view function as
                         endpoint
        :type endpoint: str
        :param view_func: the function to call when serving a request to the provided endpoint
        :type view_func: types.FunctionType
        :param options: the options to be forwarded to the underlying `werkzeug.routing.Rule` object.  A change
                        to Werkzeug is handling of method options. methods is a list of methods this rule should be
                        limited to (`GET`, `POST` etc.).  By default a rule just listens for `GET` (and implicitly
                        `HEAD`).
        """
        log_details = {'endpoint': endpoint, 'view_func': view_func.__name__}
        log_details.update(options)
        logger.debug('Adding %s', rule, extra=log_details)
        self.app.add_url_rule(rule, endpoint, view_func, **options)

    def route(self, rule, **options):
        """
        A decorator that is used to register a view function for a
        given URL rule.  This does the same thing as `add_url_rule`
        but is intended for decorator usage::

            @app.route('/')
            def index():
                return 'Hello World'

        :param rule: the URL rule as string
        :type rule: str
        :param endpoint: the endpoint for the registered URL rule.  Flask
                         itself assumes the name of the view function as
                         endpoint
        :param options: the options to be forwarded to the underlying `werkzeug.routing.Rule` object.  A change
                        to Werkzeug is handling of method options.  methods is a list of methods this rule should be
                        limited to (`GET`, `POST` etc.).  By default a rule just listens for `GET` (and implicitly
                        `HEAD`).
        """
        logger.debug('Adding %s with decorator', rule, extra=options)
        return self.app.route(rule, **options)

    def run(self, port=None, server=None, debug=None, **options):  # pragma: no cover
        """
        Runs the application on a local development server.

        :param port: port to listen to
        :type port: int
        :param server: which wsgi server to use
        :type server: str | None
        :param debug: include debugging information
        :type debug: bool
        :param options: options to be forwarded to the underlying server
        :type options: dict
        """
        # this functions is not covered in unit tests because we would effectively testing the mocks

        # overwrite constructor parameter
        if port is not None:
            self.port = port
        elif self.port is None:
            self.port = 5000

        if server is not None:
            self.server = server

        if debug is not None:
            self.debug = debug

        logger.debug('Starting %s HTTP server..', self.server, extra=vars(self))
        if self.server == 'flask':
            self.app.run('0.0.0.0', port=self.port, debug=self.debug, **options)
        elif self.server == 'tornado':
            try:
                import tornado.wsgi
                import tornado.httpserver
                import tornado.ioloop
            except:
                raise Exception('tornado library not installed')
            wsgi_container = tornado.wsgi.WSGIContainer(self.app)
            http_server = tornado.httpserver.HTTPServer(wsgi_container, **options)
            http_server.listen(self.port)
            logger.info('Listening on port %s..', port=self.port)
            tornado.ioloop.IOLoop.instance().start()
        elif self.server == 'gevent':
            try:
                import gevent.wsgi
            except:
                raise Exception('gevent library not installed')
            http_server = gevent.wsgi.WSGIServer(('', self.port), self.app, **options)
            logger.info('Listening on port %s..', self.port)
            http_server.serve_forever()
        else:
            raise Exception('Server %s not recognized', self.server)
