import logging
import pathlib

import flask
import yaml

import connexion.utils as utils

logger = logging.getLogger('connexion.api')


class Api:
    """
    Single API that corresponds to a flask blueprint
    """
    def __init__(self, swagger_yaml_path: pathlib.Path, base_url: str=None):
        self.swagger_yaml_path = pathlib.Path(swagger_yaml_path)
        logger.debug('Loading specification: %s', swagger_yaml_path)
        with swagger_yaml_path.open() as swagger_yaml:
            self.specification = yaml.load(swagger_yaml)

        # TO_DOC:
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
        endpoint_name = utils.flaskify_endpoint(operation_id)
        function = utils.get_function_from_name(operation_id)
        # TODO wrap function with json.dumps if produces is ['application/json']
        self.blueprint.add_url_rule(path, endpoint_name, function, methods=[method])

    def add_paths(self, paths: list=None):
        """
        Adds the paths defined in the specification as endpoints
        """
        paths = paths or self.specification.get('paths', dict())
        for path, methods in paths.items():
            logger.debug('Adding %s%s...', self.base_url, path)
            path = utils.flaskify_path(path)
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
        endpoint = utils.flaskify_endpoint(base_url)
        blueprint = flask.Blueprint(endpoint, __name__, url_prefix=base_url)
        return blueprint
