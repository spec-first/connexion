#!/usr/bin/env python3

import importlib
import pathlib

import flask
import tornado
import yaml


# Make flask request available here so apps don't need to import flask
request = flask.request


class App:

    # TODO also accept document that it accepts strings
    def __init__(self, import_name: str, port: int, specification_dir: pathlib.Path):
        self.app = flask.Flask(import_name)

        # we get our application root path from flask to avoid duplicating logic
        self.root_path = pathlib.Path(self.app.root_path)

        specification_dir = pathlib.Path(specification_dir)  # Ensure specification dir is a Path
        if specification_dir.is_absolute():
            self.specification_dir = specification_dir
        else:
            self.specification_dir = self.root_path / specification_dir

        self.port = port

    @staticmethod
    def flaskify_path(swagger_path: str) -> str:
        """
        Convert swagger path templates to flask path templates
        """

        # TODO ADD TYPES
        return swagger_path.replace('{', '<').replace('}', '>')

    @staticmethod
    def flaskify_endpoint(identifier: str) -> str:
        """
        Converts the provided identifier in a valid flask endpoint name
        """
        return identifier.replace('.', '_')


    # TODO also accept document that it accepts strings
    def add_api(self, swagger_file: pathlib.Path, base_path: str=None):
        # TODO test if base_url starts with an / (if not none)
        specification = self.load_specification(swagger_file, base_path)

        # base_url will either be specified, found from the specification or be '/'
        base_path = base_path or specification.get('basePath', '/')

        api_endpoint = self.flaskify_endpoint(base_path)
        api_blueprint = flask.Blueprint(api_endpoint, __name__, url_prefix=base_path)

        # Add specification json
        endpoint_name = "{name}_swagger_json".format(name=api_endpoint)
        api_blueprint.add_url_rule('/swagger.json', endpoint_name, lambda: flask.jsonify(**specification))

        paths = specification.get('paths', dict())
        for path, methods in paths.items():
            path = self.flaskify_path(path)
            # TODO Error handling
            for method, item in methods.items():
                operation_id = item['operationId']
                self.add_endpoint(api_blueprint, method, path, operation_id)

        self.app.register_blueprint(api_blueprint)

    def add_endpoint(self, api_blueprint: flask.Blueprint, method: str, path: str, operation_id:str):
        """
        Adds one endpoint to the api
        """
        endpoint_name = self.flaskify_endpoint(operation_id)
        module_name, function_name = operation_id.rsplit('.', maxsplit=1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        api_blueprint.add_url_rule(path, endpoint_name, function, methods=[method])

    # TODO also accept document that it accepts strings
    def load_specification(self, filename: pathlib.Path, base_url: str) -> dict:
        """
        Loads specification and makes some changes to make it work inside the blueprint.
        """
        yaml_path = self.specification_dir / filename
        with yaml_path.open() as swagger_yaml:
            specification = yaml.load(swagger_yaml)

        # TODO document this
        if base_url is not None:
            specification['basePath'] = base_url
        return specification

    def run(self):
        wsgi_container = tornado.wsgi.WSGIContainer(self.app)
        http_server = tornado.httpserver.HTTPServer(wsgi_container)
        http_server.listen(self.port)
        print('Listening on http://127.0.0.1:{port}/'.format(port=self.port))
        tornado.ioloop.IOLoop.instance().start()


# TODO Add swagger UI