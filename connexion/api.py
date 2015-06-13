"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import functools
import logging
import pathlib
import types

import flask
import jinja2
import yaml

from connexion.decorators.produces import jsonify
from connexion.decorators.security import verify_oauth
import connexion.utils as utils


MODULE_PATH = pathlib.Path(__file__).absolute().parent
SWAGGER_UI_PATH = MODULE_PATH / 'swagger-ui'

logger = logging.getLogger('connexion.api')


class Api:
    """
    Single API that corresponds to a flask blueprint
    """

    def __init__(self, swagger_yaml_path: pathlib.Path, base_url: str=None, arguments: dict=None):
        self.swagger_yaml_path = pathlib.Path(swagger_yaml_path)
        logger.debug('Loading specification: %s', swagger_yaml_path)
        arguments = arguments or {}
        with swagger_yaml_path.open() as swagger_yaml:
            swagger_template = swagger_yaml.read()
            swagger_string = jinja2.Template(swagger_template).render(**arguments)
            self.specification = yaml.load(swagger_string)  # type: dict

        # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields
        # TODO Validate yaml
        # If base_url is not on provided then we try to read it from the swagger.yaml or use / by default
        if base_url is None:
            self.base_url = self.specification.get('basePath', '')  # type: dict
        else:
            self.base_url = base_url
            self.specification['basePath'] = base_url

        # A list of MIME types the APIs can produce. This is global to all APIs but can be overridden on specific
        # API calls.
        self.produces = self.specification.get('produces', list())  # type: List[str]

        self.security = self.specification.get('security', [None]).pop()
        self.security_definitions = self.specification.get('securityDefinitions', dict())
        logger.debug('Security Definitions: %s', self.security_definitions)

        # Create blueprint and enpoints
        self.blueprint = self.create_blueprint()

        self.add_swagger_json()
        self.add_swagger_ui()
        self.add_paths()

    def _get_produces_decorator(self, operation: dict) -> types.FunctionType:
        """
        Get produces decorator.

        If produces == ['application/json'] then the function return value is jsonified

        From Swagger Specfication:

        **Produces**

        A list of MIME types the operation can produce. This overrides the produces definition at the Swagger Object.
        An empty value MAY be used to clear the global definition.
        """

        produces = operation['produces'] if 'produces' in operation else self.produces
        logger.debug('... Produces: %s', produces)

        if produces == ['application/json']:  # endpoint will return json
            logger.debug('... Produces json')
            return jsonify

        # If we don't know how to handle the `produces` type then we will not decorate the function
        return None

    def _get_security_decorator(self, operation: dict) -> types.FunctionType:
        """
        Gets the security decorator for operation

        From Swagger Specification:

        **Security Definitions Object**

        A declaration of the security schemes available to be used in the specification.

        This does not enforce the security schemes on the operations and only serves to provide the relevant details
        for each scheme.


        **Security Requirement Object**

        Lists the required security schemes to execute this operation. The object can have multiple security schemes
        declared in it which are all required (that is, there is a logical AND between the schemes).

        The name used for each property **MUST** correspond to a security scheme declared in the Security Definitions.
        """
        security = operation['security'].pop() if 'security' in operation else self.security
        logger.debug('... Security: %s', security)
        if security:
            if len(security) > 1:
                logger.warning("... More than security requirement defined. **IGNORING SECURITY REQUIREMENTS**")
                return None

            # the following line gets the first (and because of the previous condition only) scheme and scopes
            # from the operation's security requirements
            scheme_name, scopes = next(iter(security.items()))
            security_definition = self.security_definitions[scheme_name]
            if security_definition['type'] == 'oauth2':
                token_info_url = security_definition['x-tokenInfoUrl']
                scopes = set(scopes)  # convert scopes to set because this is needed for verify_oauth
                return functools.partial(verify_oauth, token_info_url, scopes)
            else:
                logger.warning("... Security type '%s' unknown. **IGNORING SECURITY REQUIREMENTS**",
                               security_definition['type'])

        # if we don't know how to handle the security or it's not defined we will not decorate the function
        return None

    def add_operation(self, method: str, path: str, operation: dict):
        """
        Adds one operation to the api.

        This method uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.
        """
        operation_id = operation['operationId']
        logger.debug('... Adding %s -> %s', method.upper(), operation_id)

        endpoint_name = utils.flaskify_endpoint(operation_id)
        function = utils.get_function_from_name(operation_id)

        produces_decorator = self._get_produces_decorator(operation)
        security_decorator = self._get_security_decorator(operation)

        if produces_decorator:
            logger.debug('... Adding produces decorator (%r)', produces_decorator)
            function = produces_decorator(function)
        if security_decorator:
            logger.debug('... Adding security decorator (%r)', security_decorator)
            function = security_decorator(function)

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
                self.add_operation(method, path, endpoint)

    def add_swagger_json(self):
        """
        Adds swagger json to {base_url}/swagger.json
        """
        logger.debug('Adding swagger.json: %s/swagger.json', self.base_url)
        endpoint_name = "{name}_swagger_json".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/swagger.json', endpoint_name, lambda: flask.jsonify(self.specification))

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_url}/ui/
        """
        logger.debug('Adding swagger-ui: %s/ui/', self.base_url)
        static_endpoint_name = "{name}_swagger_ui_static".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/ui/<path:filename>', static_endpoint_name, self.swagger_ui_static)
        index_endpoint_name = "{name}_swagger_ui_index".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/ui/', index_endpoint_name, self.swagger_ui_index)

    def create_blueprint(self, base_url: str=None) -> flask.Blueprint:
        base_url = base_url or self.base_url
        logger.debug('Creating API blueprint: %s', base_url)
        endpoint = utils.flaskify_endpoint(base_url)
        blueprint = flask.Blueprint(endpoint, __name__, url_prefix=base_url, template_folder=str(SWAGGER_UI_PATH))
        return blueprint

    def swagger_ui_index(self):
        return flask.render_template('index.html', api_url=self.base_url)

    @staticmethod
    def swagger_ui_static(filename: str):
        return flask.send_from_directory(str(SWAGGER_UI_PATH), filename)
