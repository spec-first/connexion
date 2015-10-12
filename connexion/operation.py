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
import os
from .decorators.parameter import parameter_to_arg
from .decorators.produces import BaseSerializer, Produces, Jsonifier
from .decorators.security import security_passthrough, verify_oauth
from .decorators.validation import RequestBodyValidator, ParameterValidator
from .decorators.metrics import UWSGIMetricsCollector
from .exceptions import InvalidSpecification
from .utils import flaskify_endpoint, get_function_from_name, produces_json

logger = logging.getLogger('connexion.operation')


class Operation:
    """
    A single API operation on a path.
    """

    def __init__(self, method, path, operation, app_produces, app_security,
                 security_definitions, definitions, parameter_definitions):
        """
        This class uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.

        :param method: HTTP method
        :type method: str
        :param path:
        :type path: str
        :param operation: swagger operation object
        :type operation: dict
        :param app_produces: list of content types the application can return by default
        :type app_produces: list
        :param app_security: list of security rules the application uses by default
        :type app_security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        :param definitions: `Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject>`_
        :type definitions: dict
        """

        self.method = method
        self.path = path
        self.security_definitions = security_definitions
        self.definitions = definitions
        self.parameter_definitions = parameter_definitions
        self.definitions_map = {
            'definitions': self.definitions,
            'parameters': self.parameter_definitions
        }

        self.operation = operation
        self.operation_id = operation['operationId']
        # todo support definition references
        # todo support references to application level parameters
        self.parameters = list(self.resolve_parameters(operation.get('parameters', [])))
        self.produces = operation.get('produces', app_produces)
        self.endpoint_name = flaskify_endpoint(self.operation_id)
        self.security = operation.get('security', app_security)
        self.__undecorated_function = get_function_from_name(self.operation_id)

    def resolve_reference(self, schema):
        schema = schema.copy()  # avoid changing the original schema
        reference = schema.get('$ref')  # type: str
        if reference:
            if not reference.startswith('#/'):
                raise InvalidSpecification(
                    "{method} {path}  '$ref' needs to start with '#/'".format(**vars(self)))
            path = reference.split('/')
            definition_type = path[1]
            try:
                definitions = self.definitions_map[definition_type]
            except KeyError:
                raise InvalidSpecification(
                    "{method} {path}  '$ref' needs to point to definitions or parameters".format(**vars(self)))
            definition_name = path[-1]
            try:
                schema.update(definitions[definition_name])
            except KeyError:
                raise InvalidSpecification("{method} {path} Definition '{definition_name}' not found".format(
                    definition_name=definition_name, method=self.method, path=self.path))
            del schema['$ref']
        return schema

    def resolve_parameters(self, parameters):
        for param in parameters:
            param = self.resolve_reference(param)
            yield param

    @property
    def body_schema(self):
        """
        `About operation parameters
        <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields-4>`_

        A list of parameters that are applicable for all the operations described under this path. These parameters can
        be overridden at the operation level, but cannot be removed there. The list MUST NOT include duplicated
        parameters. A unique parameter is defined by a combination of a name and location. The list can use the
        Reference Object to link to parameters that are defined at the Swagger Object's parameters.
        **There can be one "body" parameter at most.**

        :rtype: dict
        """
        body_parameters = [parameter for parameter in self.parameters if parameter['in'] == 'body']
        if len(body_parameters) > 1:
            raise InvalidSpecification(
                "{method} {path} There can be one 'body' parameter at most".format(**vars(self)))

        body_parameters = body_parameters[0] if body_parameters else {}
        schema = body_parameters.get('schema')  # type: dict

        if schema:
            schema = self.resolve_reference(schema)
        return schema

    @property
    def function(self):
        """
        Operation function with decorators

        :rtype: types.FunctionType
        """

        parameters = []
        for param in self.parameters:  # resolve references
            param = param.copy()
            schema = param.get('schema')
            if schema:
                schema = self.resolve_reference(schema)
            param['schema'] = schema
            parameters.append(param)
        function = parameter_to_arg(parameters, self.__undecorated_function)

        produces_decorator = self.__content_type_decorator
        logger.debug('... Adding produces decorator (%r)', produces_decorator, extra=vars(self))
        function = produces_decorator(function)

        for validation_decorator in self.__validation_decorators:
            function = validation_decorator(function)

        # NOTE: the security decorator should be applied last to check auth before anything else :-)
        security_decorator = self.__security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator, extra=vars(self))
        function = security_decorator(function)

        if UWSGIMetricsCollector.is_available():
            decorator = UWSGIMetricsCollector(self.path, self.method)
            function = decorator(function)

        return function

    @property
    def __content_type_decorator(self):
        """
        Get produces decorator.

        If the operation mimetype format is json then the function return value is jsonified

        From Swagger Specfication:

        **Produces**

        A list of MIME types the operation can produce. This overrides the produces definition at the Swagger Object.
        An empty value MAY be used to clear the global definition.

        :rtype: types.FunctionType
        """

        logger.debug('... Produces: %s', self.produces, extra=vars(self))

        if produces_json(self.produces):  # endpoint will return json
            try:
                mimetype = self.produces[0]
            except IndexError:
                # if the endpoint as no 'produces' then the default is 'application/json'
                mimetype = 'application/json'
            logger.debug('... Produces json', extra=vars(self))
            jsonify = Jsonifier(mimetype)
            return jsonify
        elif len(self.produces) == 1:
            mimetype = self.produces[0]
            logger.debug('... Produces {}'.format(mimetype), extra=vars(self))
            decorator = Produces(mimetype)
            return decorator
        else:
            return BaseSerializer()

    @property
    def __security_decorator(self):
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

        :rtype: types.FunctionType
        """
        logger.debug('... Security: %s', self.security, extra=vars(self))
        if self.security:
            if len(self.security) > 1:
                logger.warning("... More than one security requirement defined. **IGNORING SECURITY REQUIREMENTS**",
                               extra=vars(self))
                return security_passthrough

            security = self.security[0]  # type: dict
            # the following line gets the first (and because of the previous condition only) scheme and scopes
            # from the operation's security requirements

            scheme_name, scopes = next(iter(security.items()))  # type: str, list
            security_definition = self.security_definitions[scheme_name]
            if security_definition['type'] == 'oauth2':
                token_info_url = security_definition.get('x-tokenInfoUrl', os.getenv('HTTP_TOKENINFO_URL'))
                if token_info_url:
                    scopes = set(scopes)  # convert scopes to set because this is needed for verify_oauth
                    return functools.partial(verify_oauth, token_info_url, scopes)
                else:
                    logger.warning("... OAuth2 token info URL missing. **IGNORING SECURITY REQUIREMENTS**",
                                   extra=vars(self))
            elif security_definition['type'] in ('apiKey', 'basic'):
                logger.debug(
                    "... Security type '%s' not natively supported by Connexion; you should handle it yourself",
                    security_definition['type'], extra=vars(self))
            else:
                logger.warning("... Security type '%s' unknown. **IGNORING SECURITY REQUIREMENTS**",
                               security_definition['type'], extra=vars(self))

        # if we don't know how to handle the security or it's not defined we will usa a passthrough decorator
        return security_passthrough

    @property
    def __validation_decorators(self):
        """
        :rtype: types.FunctionType
        """
        if self.parameters:
            yield ParameterValidator(self.parameters)
        if self.body_schema:
            yield RequestBodyValidator(self.body_schema)
