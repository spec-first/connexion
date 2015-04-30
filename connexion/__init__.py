#!/usr/bin/env python3

import importlib
import logging
import pathlib

import flask
import tornado.wsgi
import tornado.httpserver
import tornado.ioloop
import yaml


# Make flask request available here so apps don't need to import flask
request = flask.request

logger = logging.getLogger('connexion')


def flaskify_endpoint(identifier: str) -> str:
    """
    Converts the provided identifier in a valid flask endpoint name
    """
    return identifier.replace('.', '_')


def flaskify_path(swagger_path: str) -> str:
        """
        Convert swagger path templates to flask path templates
        """

        # TODO ADD TYPES
        return swagger_path.replace('{', '<').replace('}', '>')


def get_function_from_name(operation_id: str):
        module_name, function_name = operation_id.rsplit('.', maxsplit=1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        return function


class Api:
    """
    Single API that corresponds to a flask blueprint
    """
    def __init__(self, swagger_yaml_path: pathlib.Path, base_url: str=None):
        self.swagger_yaml_path = pathlib.Path(swagger_yaml_path)
        logger.debug('Loading specification: %s', swagger_yaml_path)
        with swagger_yaml_path.open() as swagger_yaml:
            self.specification = yaml.load(swagger_yaml)

        # DOC
        # If base_url is not on provided then we try to read it from the swagger.yaml or use / by default
        if base_url is None:
            self.base_url = self.specification.get('basePath', '/')
        else:
            self.base_url = base_url
            self.specification['basePath'] = base_url

        self.blueprint = self.create_blueprint()

        self.add_swagger_json()
        self.add_paths()

    def add_endpoint(self, method: str, path: str, endpoint: dict):
        """
        Adds one endpoint to the api.
        """
        operation_id = endpoint['operationId']

        logger.debug('... adding %s -> %s', method.upper(), operation_id)
        endpoint_name = flaskify_endpoint(operation_id)
        function = get_function_from_name(operation_id)
        # TODO wrap function with json.dumps if produces is ['application/json']
        self.blueprint.add_url_rule(path, endpoint_name, function, methods=[method])

    def add_paths(self, paths: list=None):
        """
        Adds the paths defined in the specification as endpoints
        """
        paths = paths or self.specification.get('paths', dict())
        for path, methods in paths.items():
            logger.debug('Adding %s%s...', self.base_url, path)
            path = flaskify_path(path)
            # TODO Error handling
            for method, endpoint in methods.items():
                self.add_endpoint(method, path, endpoint)

    def add_swagger_json(self):
        """
        Adds swagger json to {base_url}/swagger.json
        """
        logger.debug('Adding swagger.json: %s/swagger.json', self.base_url)
        endpoint_name = "{name}_swagger_json".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/swagger.json', endpoint_name, lambda: flask.jsonify(self.specification))

    def create_blueprint(self, base_url: str=None) -> flask.Blueprint:
        base_url = base_url or self.base_url
        logger.debug('Creating API blueprint: %s', base_url)
        endpoint = flaskify_endpoint(base_url)
        blueprint = flask.Blueprint(endpoint, __name__, url_prefix=base_url)
        return blueprint


class App:

    def __init__(self, import_name: str, port: int=5000, specification_dir: pathlib.Path=''):
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

        self.port = port

    def add_api(self, swagger_file: pathlib.Path, base_path: str=None):
        logger.debug('Adding API: %s', swagger_file)
        # TODO test if base_url starts with an / (if not none)

        yaml_path = self.specification_dir / swagger_file
        api = Api(yaml_path, base_path)
        self.app.register_blueprint(api.blueprint)

    def run(self):
        wsgi_container = tornado.wsgi.WSGIContainer(self.app)
        http_server = tornado.httpserver.HTTPServer(wsgi_container)
        http_server.listen(self.port)
        logger.info('Listening on http://127.0.0.1:{port}/'.format(port=self.port))
        tornado.ioloop.IOLoop.instance().start()

# TODO Add swagger UI
