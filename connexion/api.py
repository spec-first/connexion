import functools
import logging
import pathlib
import types

import flask
import yaml
import requests

import connexion.utils as utils

MODULE_PATH = pathlib.Path(__file__).absolute().parent
SWAGGER_UI_PATH = MODULE_PATH / 'swagger-ui'

logger = logging.getLogger('connexion.api')


def jsonify(function: types.FunctionType) -> types.FunctionType:
    """
    Decorator to jsonify the return value of the wrapped function
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return flask.jsonify(function(*args, **kwargs))
    return wrapper


def verify_oauth(token_info_url: str, scope: list, function: types.FunctionType) -> types.FunctionType:
    """
    Decorator to verify oauth
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        authorization = flask.request.headers.get('Authorization')
        if authorization is None:
            logger.error('No auth provided')
            raise flask.abort(401)
        else:
            _, token = authorization.split()
            logger.error(token)
            token_request = requests.get(token_info_url, params={'access_token': token})
            logger.debug("Token verification (%d): %s", token_request.status_code, token_request.text)
            if not token_request.ok:
                raise flask.abort(401)
            # TODO verify scopes
        return function(*args, **kwargs)
    return wrapper


def swagger_ui_index(api_url):
    return flask.render_template('index.html', api_url=api_url)


def swagger_ui_static(filename: str):
    return flask.send_from_directory(str(SWAGGER_UI_PATH), filename)


class Api:
    """
    Single API that corresponds to a flask blueprint
    """
    def __init__(self, swagger_yaml_path: pathlib.Path, base_url: str=None):
        self.swagger_yaml_path = pathlib.Path(swagger_yaml_path)
        logger.debug('Loading specification: %s', swagger_yaml_path)
        with swagger_yaml_path.open() as swagger_yaml:
            self.specification = yaml.load(swagger_yaml)

        # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields
        # TODO Validate yaml
        # TO_DOC:
        # If base_url is not on provided then we try to read it from the swagger.yaml or use / by default
        if base_url is None:
            self.base_url = self.specification.get('basePath', '')  # type: dict
        else:
            self.base_url = base_url
            self.specification['basePath'] = base_url

        # A list of MIME types the APIs can produce. This is global to all APIs but can be overridden on specific
        # API calls.
        self.produces = self.specification.get('produces', list())  # type: List[str]

        self.security = self.specification.get('security', None)
        self.security_definitions = self.specification.get('securityDefinitions', dict())

        # Create blueprint and enpoints
        self.blueprint = self.create_blueprint()

        self.add_swagger_json()
        self.add_swagger_ui()
        self.add_paths()

    def add_endpoint(self, method: str, path: str, operation: dict):
        """
        Adds one endpoint to the api.
        """
        # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields-5
        # From Spec: A friendly name for the operation. The id MUST be unique among all operations described in the API.
        #            Tools and libraries MAY use the operation id to uniquely identify an operation.
        # In connexion: Used to identify the module and function
        operation_id = operation['operationId']
        logger.debug('... adding %s -> %s', method.upper(), operation_id)

        # From Spec: A list of MIME types the operation can produce. This overrides the produces definition at the
        #            Swagger Object. An empty value MAY be used to clear the global definition.
        # In connexion: if produces == ['application/json'] then the function return value s jsonified
        produces = operation['produces'] if 'produces' in operation else self.produces
        returns_json = produces == ['application/json']

        security = operation['security'] if 'security' in operation else self.security
        security_decorator = None
        if security:
            if len(security) > 1:
                raise Exception('INVALID DEFINITION: Connexion only supports one authentication for operation')
                # TODO Proper invalid definition exception

            for scheme in security:
                security_definition = self.security_definitions[scheme]
            if security_definition['type'] == 'oauth2':
                token_info_url = security_definition['x-tokenInfoUrl']  # TODO Document custom property
                # and that connexion adds authentication
                scopes = security_definition['scopes']
                security_decorator = functools.partial(verify_oauth, token_info_url, scopes)
            else:
                logger.debug("... Security type '%s' ignored", security_definition['type'])

        endpoint_name = utils.flaskify_endpoint(operation_id)
        function = utils.get_function_from_name(operation_id)
        if returns_json:
            function = jsonify(function)
        if security_decorator:
            logger.debug('... Adding security decorator')
            function = security_decorator(function)
        # TODO document that connexions wraps function with jsonify if produces is ['application/json']
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

    def add_swagger_ui(self):
        """
        Adds swagger ui to base_url}/ui/
        """
        logger.debug('Adding swagger-ui: %s/ui/', self.base_url)
        static_endpoint_name = "{name}_swagger_ui_static".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/ui/<path:filename>', static_endpoint_name, swagger_ui_static)
        index_endpoint_name = "{name}_swagger_ui_index".format(name=self.blueprint.name)
        partial_index = functools.partial(swagger_ui_index, self.base_url)
        self.blueprint.add_url_rule('/ui/', index_endpoint_name, partial_index)

    def create_blueprint(self, base_url: str=None) -> flask.Blueprint:
        base_url = base_url or self.base_url
        logger.debug('Creating API blueprint: %s', base_url)
        endpoint = utils.flaskify_endpoint(base_url)
        blueprint = flask.Blueprint(endpoint, __name__, url_prefix=base_url, template_folder=str(SWAGGER_UI_PATH))
        return blueprint
