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
from copy import deepcopy

from jsonschema import ValidationError

from .decorators import validation
from .decorators.metrics import UWSGIMetricsCollector
from .decorators.parameter import parameter_to_arg
from .decorators.produces import BaseSerializer, Jsonifier, Produces
from .decorators.response import ResponseValidator
from .decorators.security import (get_tokeninfo_url, security_passthrough,
                                  verify_oauth)
from .decorators.validation import (ParameterValidator, RequestBodyValidator,
                                    TypeValidationError)
from .exceptions import InvalidSpecification
from .utils import all_json, flaskify_endpoint, is_nullable

logger = logging.getLogger('connexion.operation')


class SecureOperation(object):
    def __init__(self, security, security_definitions):
        """
        :param security: list of security rules the application uses by default
        :type security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        """
        self.security = security
        self.security_definitions = security_definitions

    @property
    def security_decorator(self):
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
                token_info_url = get_tokeninfo_url(security_definition)
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

        # if we don't know how to handle the security or it's not defined we will usa a passthrough decorator
        return security_passthrough


class Operation(SecureOperation):
    DEFAULT_MIMETYPE = 'application/json'

    """
    A single API operation on a path.
    """

    def __init__(self, method, path, operation, resolver, app_produces, app_consumes,
                 path_parameters=None, app_security=None, security_definitions=None,
                 definitions=None, parameter_definitions=None, response_definitions=None,
                 validate_responses=False, strict_validation=False, randomize_endpoint=None):
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
        :param resolver: Callable that maps operationID to a function
        :param app_produces: list of content types the application can return by default
        :type app_produces: list
        :param app_consumes: list of content types the application consumes by default
        :type app_consumes: list
        :param path_parameters: Parameters defined in the path level
        :type path_parameters: list
        :param app_security: list of security rules the application uses by default
        :type app_security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        :param definitions: `Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject>`_
        :type definitions: dict
        :param parameter_definitions: Global parameter definitions
        :type parameter_definitions: dict
        :param response_definitions: Global response definitions
        :type response_definitions: dict
        :param validate_responses: True enables validation. Validation errors generate HTTP 500 responses.
        :type validate_responses: bool
        :param strict_validation: True enables validation on invalid request parameters
        :type strict_validation: bool
        """

        self.method = method
        self.path = path
        self.security_definitions = security_definitions or {}
        self.definitions = definitions or {}
        self.parameter_definitions = parameter_definitions or {}
        self.response_definitions = response_definitions or {}
        self.definitions_map = {
            'definitions': self.definitions,
            'parameters': self.parameter_definitions,
            'responses': self.response_definitions
        }
        self.validate_responses = validate_responses
        self.strict_validation = strict_validation
        self.operation = operation
        self.randomize_endpoint = randomize_endpoint

        # todo support definition references
        # todo support references to application level parameters
        self.parameters = list(self.resolve_parameters(operation.get('parameters', [])))
        if path_parameters:
            self.parameters += list(self.resolve_parameters(path_parameters))

        self.security = operation.get('security', app_security)
        self.produces = operation.get('produces', app_produces)
        self.consumes = operation.get('consumes', app_consumes)

        resolution = resolver.resolve(self)
        self.operation_id = resolution.operation_id
        self.endpoint_name = flaskify_endpoint(self.operation_id, self.randomize_endpoint)
        self.__undecorated_function = resolution.function

        self.validate_defaults()

    def validate_defaults(self):
        for param in self.parameters:
            try:
                if param['in'] == 'query' and 'default' in param:
                    validation.validate_type(param, param['default'], 'query', param['name'])
            except (TypeValidationError, ValidationError):
                raise InvalidSpecification('The parameter \'{param_name}\' has a default value which is not of'
                                           ' type \'{param_type}\''.format(param_name=param['name'],
                                                                           param_type=param['type']))

    def resolve_reference(self, schema):
        schema = deepcopy(schema)  # avoid changing the original schema
        self.check_references(schema)

        # find the object we need to resolve/update if this is not a proper SchemaObject
        # e.g a response or parameter object
        for obj in schema, schema.get('items'):
            reference = obj and obj.get('$ref')  # type: str
            if reference:
                break
        if reference:
            definition = deepcopy(self._retrieve_reference(reference))
            # Update schema
            obj.update(definition)
            del obj['$ref']

        # if there is a schema object on this param or response, then we just
        # need to include the defs and it can be validated by jsonschema
        if 'schema' in schema:
            schema['schema']['definitions'] = self.definitions
            return schema

        return schema

    def check_references(self, schema):
        """
        Searches the keys and values of a schema object for json references.
        If it finds one, it attempts to locate it and will thrown an exception
        if the reference can't be found in the definitions dictionary.

        :param schema: The schema object to check
        :type schema: dict
        :raises InvalidSpecification: raised when a reference isn't found
        """

        stack = [schema]
        visited = set()
        while stack:
            schema = stack.pop()
            for k, v in schema.items():
                if k == "$ref":
                    if v in visited:
                        continue
                    visited.add(v)
                    stack.append(self._retrieve_reference(v))
                elif isinstance(v, (list, tuple)):
                    continue
                elif hasattr(v, "items"):
                    stack.append(v)

    def _retrieve_reference(self, reference):
        if not reference.startswith('#/'):
            raise InvalidSpecification(
                "{method} {path} '$ref' needs to start with '#/'".format(**vars(self)))
        path = reference.split('/')
        definition_type = path[1]
        try:
            definitions = self.definitions_map[definition_type]
        except KeyError:
            ref_possible = ', '.join(self.definitions_map.keys())
            raise InvalidSpecification(
                "{method} {path} $ref \"{reference}\" needs to point to one of: "
                "{ref_possible}".format(
                    method=self.method,
                    path=self.path,
                    reference=reference,
                    ref_possible=ref_possible
                ))
        definition_name = path[-1]
        try:
            # Get sub definition
            definition = deepcopy(definitions[definition_name])
        except KeyError:
            raise InvalidSpecification(
                "{method} {path} Definition '{definition_name}' not found".format(
                    definition_name=definition_name, method=self.method, path=self.path))

        return definition

    def get_mimetype(self):
        """
        If the endpoint has no 'produces' then the default is
        'application/json'.

        :rtype str
        """
        if all_json(self.produces):
            try:
                return self.produces[0]
            except IndexError:
                return Operation.DEFAULT_MIMETYPE
        elif len(self.produces) == 1:
            return self.produces[0]
        else:
            return Operation.DEFAULT_MIMETYPE

    def resolve_parameters(self, parameters):
        for param in parameters:
            param = self.resolve_reference(param)
            yield param

    def get_path_parameter_types(self):
        return {p['name']: p.get('type') for p in self.parameters if p['in'] == 'path'}

    @property
    def body_schema(self):
        """
        The body schema definition for this operation.
        """
        return self.body_definition.get('schema')

    @property
    def body_definition(self):
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**

        :rtype: dict
        """
        body_parameters = [parameter for parameter in self.parameters if parameter['in'] == 'body']
        if len(body_parameters) > 1:
            raise InvalidSpecification(
                "{method} {path} There can be one 'body' parameter at most".format(**vars(self)))

        return body_parameters[0] if body_parameters else {}

    @property
    def function(self):
        """
        Operation function with decorators

        :rtype: types.FunctionType
        """

        function = parameter_to_arg(self.parameters, self.consumes, self.__undecorated_function)

        if self.validate_responses:
            logger.debug('... Response validation enabled.')
            response_decorator = self.__response_validation_decorator
            logger.debug('... Adding response decorator (%r)', response_decorator)
            function = response_decorator(function)

        produces_decorator = self.__content_type_decorator
        logger.debug('... Adding produces decorator (%r)', produces_decorator, extra=vars(self))
        function = produces_decorator(function)

        for validation_decorator in self.__validation_decorators:
            function = validation_decorator(function)

        # NOTE: the security decorator should be applied last to check auth before anything else :-)
        security_decorator = self.security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator, extra=vars(self))
        function = security_decorator(function)

        if UWSGIMetricsCollector.is_available():  # pragma: no cover
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

        mimetype = self.get_mimetype()
        if all_json(self.produces):  # endpoint will return json
            logger.debug('... Produces json', extra=vars(self))
            jsonify = Jsonifier(mimetype)
            return jsonify
        elif len(self.produces) == 1:
            logger.debug('... Produces %s', mimetype, extra=vars(self))
            decorator = Produces(mimetype)
            return decorator
        else:
            return BaseSerializer()

    @property
    def __validation_decorators(self):
        """
        :rtype: types.FunctionType
        """
        if self.parameters:
            yield ParameterValidator(self.parameters, strict_validation=self.strict_validation)
        if self.body_schema:
            yield RequestBodyValidator(self.body_schema, self.consumes,
                                       is_nullable(self.body_definition))

    @property
    def __response_validation_decorator(self):
        """
        Get a decorator for validating the generated Response.
        :rtype: types.FunctionType
        """
        return ResponseValidator(self, self.get_mimetype())
