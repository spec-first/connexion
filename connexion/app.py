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
import types

import flask
import tornado.wsgi
import tornado.httpserver
import tornado.ioloop
import werkzeug.exceptions

from connexion.problem import problem
import connexion.api

logger = logging.getLogger('api')


class App:

    def __init__(self, import_name: str, port: int=5000, specification_dir: pathlib.Path='', server: str=None,
                 arguments: dict=None, debug: bool=False):
        """
        :param import_name: the name of the application package
        :param port: port to listen to
        :param specification_dir: directory where to look for specifications
        :param server: which wsgi server to use
        :param arguments: arguments to replace on the specification
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
        self.server = server
        self.debug = debug
        self.arguments = arguments or {}

    def add_api(self, swagger_file: pathlib.Path, base_path: str=None, arguments: dict=None):
        """
        :param swagger_file: swagger file with the specification
        :param base_path: base path where to add this api
        :param arguments: api version specific arguments to replace on the specification
        """
        logger.debug('Adding API: %s', swagger_file)
        # TODO test if base_url starts with an / (if not none)
        arguments = arguments or dict()
        arguments = dict(self.arguments, **arguments)  # copy global arguments and update with api specfic
        yaml_path = self.specification_dir / swagger_file
        api = connexion.api.Api(yaml_path, base_path, arguments)
        self.app.register_blueprint(api.blueprint)

    def add_error_handler(self, error_code: int, function: types.FunctionType):
        self.app.error_handler_spec[None][error_code] = function

    @staticmethod
    def common_error_handler(e: werkzeug.exceptions.HTTPException):
        if not isinstance(e, werkzeug.exceptions.HTTPException):
            e = werkzeug.exceptions.InternalServerError()
        return problem(title=e.name, detail=e.description, status=e.code)

    def run(self):

        if self.server is None:
            self.app.run('0.0.0.0', port=self.port, debug=self.debug)
        elif self.server == 'tornado':
            wsgi_container = tornado.wsgi.WSGIContainer(self.app)
            http_server = tornado.httpserver.HTTPServer(wsgi_container)
            http_server.listen(self.port)
            logger.info('Listening on http://127.0.0.1:{port}/'.format(port=self.port))
            tornado.ioloop.IOLoop.instance().start()
        else:
            raise Exception('Server {} not recognized'.format(self.server))
