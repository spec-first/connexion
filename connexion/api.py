"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import copy
import json
import logging
import pathlib
import sys

import flask
import jinja2
import six
import werkzeug.exceptions
import yaml
from swagger_spec_validator.validator20 import validate_spec

from . import resolver, utils
from .handlers import AuthErrorHandler
from .operation import Operation

MODULE_PATH = pathlib.Path(__file__).absolute().parent
SWAGGER_UI_PATH = MODULE_PATH / 'vendor' / 'swagger-ui'
SWAGGER_UI_URL = 'ui'

logger = logging.getLogger('connexion.api')


def compatibility_layer(spec):
    """Make specs compatible with older versions of Connexion."""
    # Make all response codes be string
    for path_name, methods_available in spec.get('paths', {}).items():
        for method_name, method_def in methods_available.items():
            if (method_name == 'parameters' or not isinstance(
                    method_def, dict)):
                continue

            response_definitions = {}
            for response_code, response_def in method_def.get(
                    'responses', {}).items():
                response_definitions[str(response_code)] = response_def

            method_def['responses'] = response_definitions
    return spec


class Api(object):
    """
    Single API that corresponds to a flask blueprint
    """

    def __init__(self, swagger_yaml_path, base_url=None, arguments=None,
                 swagger_json=None, swagger_ui=None, swagger_path=None, swagger_url=None,
                 validate_responses=False, resolver=resolver.Resolver(),
                 auth_all_paths=False, debug=False):
        """
        :type swagger_yaml_path: pathlib.Path
        :type base_url: str | None
        :type arguments: dict | None
        :type swagger_json: bool
        :type swagger_ui: bool
        :type swagger_path: string | None
        :type swagger_url: string | None
        :type auth_all_paths: bool
        :type debug: bool
        :param resolver: Callable that maps operationID to a function
        """
        self.debug = debug
        self.swagger_yaml_path = pathlib.Path(swagger_yaml_path)
        logger.debug('Loading specification: %s', swagger_yaml_path,
                     extra={'swagger_yaml': swagger_yaml_path,
                            'base_url': base_url,
                            'arguments': arguments,
                            'swagger_ui': swagger_ui,
                            'swagger_path': swagger_path,
                            'swagger_url': swagger_url,
                            'auth_all_paths': auth_all_paths})
        arguments = arguments or {}
        with swagger_yaml_path.open() as swagger_yaml:
            swagger_template = swagger_yaml.read()
            swagger_string = jinja2.Template(swagger_template).render(**arguments)
            self.specification = yaml.load(swagger_string)  # type: dict

        logger.debug('Read specification', extra=self.specification)

        self.specification = compatibility_layer(self.specification)
        # Avoid validator having ability to modify specification
        spec = copy.deepcopy(self.specification)
        validate_spec(spec)

        # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields
        # If base_url is not on provided then we try to read it from the swagger.yaml or use / by default
        if base_url is None:
            self.base_url = self.specification.get('basePath', '')  # type: dict
        else:
            self.base_url = base_url
            self.specification['basePath'] = base_url

        # A list of MIME types the APIs can produce. This is global to all APIs but can be overridden on specific
        # API calls.
        self.produces = self.specification.get('produces', list())  # type: List[str]

        self.security = self.specification.get('security')
        self.security_definitions = self.specification.get('securityDefinitions', dict())
        logger.debug('Security Definitions: %s', self.security_definitions)

        self.definitions = self.specification.get('definitions', {})
        self.parameter_definitions = self.specification.get('parameters', {})
        self.response_definitions = self.specification.get('responses', {})

        self.swagger_path = swagger_path or SWAGGER_UI_PATH
        self.swagger_url = swagger_url or SWAGGER_UI_URL

        self.resolver = resolver

        logger.debug('Validate Responses: %s', str(validate_responses))
        self.validate_responses = validate_responses

        # Create blueprint and endpoints
        self.blueprint = self.create_blueprint()

        if swagger_json:
            self.add_swagger_json()
        if swagger_ui:
            self.add_swagger_ui()

        self.add_paths()

        if auth_all_paths:
            self.add_auth_on_not_found()

    def add_operation(self, method, path, swagger_operation, path_parameters):
        """
        Adds one operation to the api.

        This method uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.

        :type method: str
        :type path: str
        :type swagger_operation: dict
        """
        operation = Operation(method=method,
                              path=path,
                              path_parameters=path_parameters,
                              operation=swagger_operation,
                              app_produces=self.produces,
                              app_security=self.security,
                              security_definitions=self.security_definitions,
                              definitions=self.definitions,
                              parameter_definitions=self.parameter_definitions,
                              response_definitions=self.response_definitions,
                              validate_responses=self.validate_responses,
                              resolver=self.resolver)
        operation_id = operation.operation_id
        logger.debug('... Adding %s -> %s', method.upper(), operation_id,
                     extra=vars(operation))

        flask_path = utils.flaskify_path(path, operation.get_path_parameter_types())
        self.blueprint.add_url_rule(flask_path, operation.endpoint_name, operation.function, methods=[method])

    def add_paths(self, paths=None):
        """
        Adds the paths defined in the specification as endpoints

        :type paths: list
        """
        paths = paths or self.specification.get('paths', dict())
        for path, methods in paths.items():
            logger.debug('Adding %s%s...', self.base_url, path)

            # search for parameters definitions in the path level
            # http://swagger.io/specification/#pathItemObject
            path_parameters = methods.get('parameters', [])

            # TODO Error handling
            for method, endpoint in methods.items():
                if method == 'parameters':
                    continue
                try:
                    self.add_operation(method, path, endpoint, path_parameters)
                except Exception:  # pylint: disable= W0703
                    url = '{base_url}{path}'.format(base_url=self.base_url,
                                                    path=path)
                    error_msg = 'Failed to add operation for {method} {url}'.format(
                        method=method.upper(),
                        url=url)
                    if self.debug:
                        logger.exception(error_msg)
                    else:
                        logger.error(error_msg)
                        six.reraise(*sys.exc_info())

    def add_auth_on_not_found(self):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug('Adding path not found authentication')
        not_found_error = AuthErrorHandler(werkzeug.exceptions.NotFound(), security=self.security,
                                           security_definitions=self.security_definitions)
        endpoint_name = "{name}_not_found".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/<path:invalid_path>', endpoint_name, not_found_error.function)

    def add_swagger_json(self):
        """
        Adds swagger json to {base_url}/swagger.json
        """
        logger.debug('Adding swagger.json: %s/swagger.json', self.base_url)
        endpoint_name = "{name}_swagger_json".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/swagger.json', endpoint_name, lambda: json.dumps(self.specification))

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_url}/ui/
        """
        logger.debug('Adding swagger-ui: %s/%s/', self.base_url, self.swagger_url)
        static_endpoint_name = "{name}_swagger_ui_static".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/{swagger_url}/<path:filename>'.format(swagger_url=self.swagger_url),
                                    static_endpoint_name, self.swagger_ui_static)
        index_endpoint_name = "{name}_swagger_ui_index".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/{swagger_url}/'.format(swagger_url=self.swagger_url),
                                    index_endpoint_name, self.swagger_ui_index)

    def create_blueprint(self, base_url=None):
        """
        :type base_url: str | None
        :rtype: flask.Blueprint
        """
        base_url = base_url or self.base_url
        logger.debug('Creating API blueprint: %s', base_url)
        endpoint = utils.flaskify_endpoint(base_url)
        blueprint = flask.Blueprint(endpoint, __name__, url_prefix=base_url,
                                    template_folder=str(self.swagger_path))
        return blueprint

    def swagger_ui_index(self):
        return flask.render_template('index.html', api_url=self.base_url)

    def swagger_ui_static(self, filename):
        """
        :type filename: str
        """
        return flask.send_from_directory(str(self.swagger_path), filename)
