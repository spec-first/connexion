import functools
import logging
from copy import deepcopy

from jsonschema import ValidationError

from .decorators import validation
from .decorators.decorator import (BeginOfRequestLifecycleDecorator,
                                   EndOfRequestLifecycleDecorator)
from .decorators.metrics import UWSGIMetricsCollector
from .decorators.parameter import parameter_to_arg
from .decorators.produces import BaseSerializer, Produces
from .decorators.response import ResponseValidator
from .decorators.security import (get_tokeninfo_func, get_tokeninfo_url,
                                  security_passthrough, verify_oauth_local,
                                  verify_oauth_remote)
from .decorators.uri_parsing import AlwaysMultiURIParser
from .decorators.validation import (ParameterValidator, RequestBodyValidator,
                                    TypeValidationError)
from .exceptions import InvalidSpecification
from .utils import all_json, deep_get, is_nullable

logger = logging.getLogger('connexion.operation')

DEFAULT_MIMETYPE = 'application/json'


VALIDATOR_MAP = {
    'parameter': ParameterValidator,
    'body': RequestBodyValidator,
    'response': ResponseValidator,
}


class SecureOperation(object):

    def __init__(self, api, security, security_definitions):
        """
        :param security: list of security rules the application uses by default
        :type security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        """
        self.api = api
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
                logger.debug("... More than one security requirement defined. **IGNORING SECURITY REQUIREMENTS**",
                             extra=vars(self))
                return security_passthrough

            security = self.security[0]  # type: dict
            # the following line gets the first (and because of the previous condition only) scheme and scopes
            # from the operation's security requirements

            scheme_name, scopes = next(iter(security.items()))  # type: str, list
            security_definition = self.security_definitions[scheme_name]
            if security_definition['type'] == 'oauth2':
                token_info_url = get_tokeninfo_url(security_definition)
                token_info_func = get_tokeninfo_func(security_definition)
                scopes = set(scopes)  # convert scopes to set because this is needed for verify_oauth_remote

                if token_info_url and token_info_func:
                    logger.warning("... Both x-tokenInfoUrl and x-tokenInfoFunc are defined, using x-tokenInfoFunc",
                                   extra=vars(self))
                if token_info_func:
                    return functools.partial(verify_oauth_local, token_info_func, scopes)
                if token_info_url:
                    return functools.partial(verify_oauth_remote, token_info_url, scopes)
                else:
                    logger.warning("... OAuth2 token info URL missing. **IGNORING SECURITY REQUIREMENTS**",
                                   extra=vars(self))
            elif security_definition['type'] in ('apiKey', 'basic'):
                logger.debug(
                    "... Security type '%s' not natively supported by Connexion; you should handle it yourself",
                    security_definition['type'], extra=vars(self))

        # if we don't know how to handle the security or it's not defined we will usa a passthrough decorator
        return security_passthrough

    def get_mimetype(self):
        return DEFAULT_MIMETYPE

    @property
    def _request_begin_lifecycle_decorator(self):
        """
        Transforms the result of the operation handler in a internal
        representation (connexion.lifecycle.ConnexionRequest) to be
        used by internal Connexion decorators.

        :rtype: types.FunctionType
        """
        return BeginOfRequestLifecycleDecorator(self.api, self.get_mimetype())

    @property
    def _request_end_lifecycle_decorator(self):
        """
        Guarantees that instead of the internal representation of the
        operation handler response
        (connexion.lifecycle.ConnexionRequest) a framework specific
        object is returned.
        :rtype: types.FunctionType
        """
        return EndOfRequestLifecycleDecorator(self.api, self.get_mimetype())


class Operation(SecureOperation):

    """
    A single API operation on a path.
    """

    def __init__(self, api, method, path, operation, resolver, path_parameters=None,
                 app_security=None, components=None, validate_responses=False,
                 strict_validation=False, randomize_endpoint=None, validator_map=None,
                 pythonic_params=False, uri_parser_class=None):
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
        :param validator_map: map of validators
        :type validator_map: dict
        :param path_parameters: Parameters defined in the path level
        :type path_parameters: list
        :param app_security: list of security rules the application uses by default
        :type app_security: list
        :param components: `Components Object
            <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md#componentsObject>`_
        :type components: dict
        :param validate_responses: True enables validation. Validation errors generate HTTP 500 responses.
        :type validate_responses: bool
        :param strict_validation: True enables validation on invalid request parameters
        :type strict_validation: bool
        :param randomize_endpoint: number of random characters to append to operation name
        :type randomize_endpoint: integer
        :param validator_map: Custom validators for the types "parameter", "body" and "response".
        :type validator_map: dict
        :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended
        to any shadowed built-ins
        :type pythonic_params: bool
        :param uri_parser_class: A URI parser class that inherits from AbstractURIParser
        :type uri_parser_class: AbstractURIParser
        """

        self.api = api
        self.method = method
        self.path = path
        self.validator_map = dict(VALIDATOR_MAP)
        self.validator_map.update(validator_map or {})

        self.components = components or {}
        self.definitions = None  # XXX

        def component_get(oas3_name):
            return self.components.get(oas3_name, {})

        self.security_definitions = component_get('securitySchemes')
        self.parameter_definitions = component_get('parameters')
        self.response_definitions = component_get('responses')

        self.definitions_map = {
            'components': {
                'schemas': component_get('schemas'),
                'requestBodies': component_get('requestBodies'),
                'parameters': component_get('parameters'),
                'securitySchemes': component_get('securitySchemes'),
                'responses': component_get('responses'),
                'headers': component_get('headers'),
            }
        }
        self.validate_responses = validate_responses
        self.strict_validation = strict_validation
        self.operation = operation
        self.randomize_endpoint = randomize_endpoint
        self.pythonic_params = pythonic_params
        self.uri_parser_class = uri_parser_class or AlwaysMultiURIParser

        # todo support definition references
        # todo support references to application level parameters
        self.request_body = operation.get('requestBody')
        if self.request_body:
            self.request_body = self.resolve_reference(self.request_body)

        self.parameters = list(self.resolve_parameters(operation.get('parameters', [])))
        if path_parameters:
            self.parameters += list(self.resolve_parameters(path_parameters))

        self.security = operation.get('security', app_security)

        # TODO figure out how to support multiple mimetypes
        # NOTE we currently just combine all of the possible mimetypes,
        #      but we need to refactor to support mimetypes by response code
        response_codes = operation.get('responses', {})
        response_content_types = []
        for _, defn in response_codes.items():
            response_content_types += defn.get('content', {}).keys()
        self.produces = response_content_types or ['application/json']

        request_content = operation.get('requestBody', {}).get('content', {})
        self.consumes = list(request_content.keys()) or ['application/json']

        logger.debug('consumes: %s' % self.consumes)
        logger.debug('produces: %s' % self.produces)

        resolution = resolver.resolve(self)
        self.operation_id = resolution.operation_id
        self._undecorated_function = resolution.function

        self.validate_defaults()

    def validate_defaults(self):
        for param_defn in self.parameters:
            try:
                param_schema = param_defn["schema"]
                if param_defn['in'] == 'query' and 'default' in param_schema:
                    validation.validate_type(param_defn, param_schema['default'],
                                             'query', param_defn['name'])
            except (TypeValidationError, ValidationError):
                raise InvalidSpecification('The parameter \'{param_name}\' has a default value which is not of'
                                           ' type \'{param_type}\''.format(param_name=param_defn['name'],
                                                                           param_type=param_schema['type']))

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

        # if the schema includes allOf or oneOf or anyOf
        for multi in ['allOf', 'anyOf', 'oneOf']:
            upd = []
            for s in schema.get(multi, []):
                upd.append(self.resolve_reference(s))
            if upd:
                schema[multi] = upd

        # additionalProperties
        try:
            ap = schema['additionalProperties']
            if ap:
                schema['additionalProperties'] = self.resolve_reference(ap)
        except KeyError:
            pass

        # if there is a schema object on this param or response, then we just
        # need to include the defs and it can be validated by jsonschema
        if "schema" in schema:
            if self.definitions:
                schema['schema']['definitions'] = self.definitions
            if self.components:
                schema['schema']['components'] = self.components
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
        path = reference[2:].split('/')
        try:
            definition = deep_get(self.definitions_map, path)
        except KeyError:
            raise InvalidSpecification(
                "{method} {path} $ref '{reference}' not found".format(
                    reference=reference, method=self.method, path=self.path))

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
                return DEFAULT_MIMETYPE
        elif len(self.produces) == 1:
            return self.produces[0]
        else:
            return DEFAULT_MIMETYPE

    def resolve_parameters(self, parameters):
        for param in parameters:
            param = self.resolve_reference(param)
            yield param

    def resolve_request_body(self, request_body):
        return self.resolve_reference(request_body)

    def get_path_parameter_types(self):
        types = {}
        path_parameters = (p for p in self.parameters if p["in"] == "path")
        for path_defn in path_parameters:
            path_schema = path_defn["schema"]
            if path_schema.get('type') == 'string' and path_schema.get('format') == 'path':
                # path is special case for type 'string'
                path_type = 'path'
            else:
                path_type = path_schema.get('type')
            types[path_defn['name']] = path_type
        return types

    @property
    def body_schema(self):
        """
        The body schema definition for this operation.
        """
        return self.resolve_reference(self.body_definition.get('schema', {}))

    @property
    def body_definition(self):
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**

        :rtype: dict
        """
        if self.request_body:
            # oas3
            if len(self.consumes) > 1:
                logger.warning(
                    'this operation accepts multiple content types, using %s',
                    self.consumes[0])
            res = self.request_body.get('content', {}).get(self.consumes[0], {})
            return self.resolve_reference(res)
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

        function = parameter_to_arg(
            self.parameters, self.body_schema, self.consumes, self._undecorated_function,
            self.pythonic_params)
        function = self._request_begin_lifecycle_decorator(function)

        if self.validate_responses:
            logger.debug('... Response validation enabled.')
            response_decorator = self.__response_validation_decorator
            logger.debug('... Adding response decorator (%r)', response_decorator)
            function = response_decorator(function)

        produces_decorator = self.__content_type_decorator
        logger.debug('... Adding produces decorator (%r)', produces_decorator)
        function = produces_decorator(function)

        for validation_decorator in self.__validation_decorators:
            function = validation_decorator(function)

        uri_parsing_decorator = self.__uri_parsing_decorator
        logging.debug('... Adding uri parsing decorator (%r)', uri_parsing_decorator)
        function = uri_parsing_decorator(function)

        # NOTE: the security decorator should be applied last to check auth before anything else :-)
        security_decorator = self.security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator)
        function = security_decorator(function)

        if UWSGIMetricsCollector.is_available():  # pragma: no cover
            decorator = UWSGIMetricsCollector(self.path, self.method)
            function = decorator(function)

        function = self._request_end_lifecycle_decorator(function)

        return function

    @property
    def __uri_parsing_decorator(self):
        """
        Get uri parsing decorator

        This decorator handles query and path parameter deduplication and
        array types.
        """
        return self.uri_parser_class(self.parameters)

    @property
    def __content_type_decorator(self):
        """
        Get produces decorator.

        If the operation mimetype format is json then the function return value is jsonified

        From Swagger Specification:

        **Produces**

        A list of MIME types the operation can produce. This overrides the produces definition at the Swagger Object.
        An empty value MAY be used to clear the global definition.

        :rtype: types.FunctionType
        """

        logger.debug('... Produces: %s', self.produces, extra=vars(self))

        mimetype = self.get_mimetype()
        if all_json(self.produces):  # endpoint will return json
            logger.debug('... Produces json', extra=vars(self))
            # TODO: Refactor this.
            return lambda f: f

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
        ParameterValidator = self.validator_map['parameter']
        RequestBodyValidator = self.validator_map['body']
        if self.parameters:
            yield ParameterValidator(self.parameters,
                                     self.api,
                                     strict_validation=self.strict_validation)
        if self.body_schema:
            yield RequestBodyValidator(self.body_schema, self.consumes, self.api,
                                       is_nullable(self.body_definition),
                                       strict_validation=self.strict_validation)

    @property
    def __response_validation_decorator(self):
        """
        Get a decorator for validating the generated Response.
        :rtype: types.FunctionType
        """
        ResponseValidator = self.validator_map['response']
        return ResponseValidator(self, self.get_mimetype())

    def json_loads(self, data):
        """
        A wrapper for calling the API specific JSON loader.

        :param data: The JSON data in textual form.
        :type data: bytes
        """
        return self.api.json_loads(data)


class Swagger2Operation(Operation):

    def __init__(self, api, method, path, operation, resolver, app_produces, app_consumes,
                 path_parameters=None, app_security=None, security_definitions=None,
                 definitions=None, parameter_definitions=None,
                 response_definitions=None, validate_responses=False, strict_validation=False,
                 randomize_endpoint=None, validator_map=None, pythonic_params=False):
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
        :param validator_map: map of validators
        :type validator_map: dict
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
        :param validator_map: Custom validators for the types "parameter", "body" and "response".
        :type validator_map: dict
        :param validate_responses: True enables validation. Validation errors generate HTTP 500 responses.
        :type validate_responses: bool
        :param strict_validation: True enables validation on invalid request parameters
        :type strict_validation: bool
        :param randomize_endpoint: number of random characters to append to operation name
        :type randomize_endpoint: integer
        :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended
        to any shadowed built-ins
        :type pythonic_params: bool
        """

        self.api = api
        self.method = method
        self.path = path
        self.validator_map = dict(VALIDATOR_MAP)
        self.validator_map.update(validator_map or {})

        self.definitions = definitions
        self.components = None

        self.security_definitions = security_definitions
        self.parameter_definitions = parameter_definitions
        self.response_definitions = response_definitions

        self.definitions_map = {
            'components': {},
            'definitions': self.definitions,
            'parameters': self.parameter_definitions,
            'responses': self.response_definitions
        }
        self.validate_responses = validate_responses
        self.strict_validation = strict_validation
        self.operation = operation
        self.randomize_endpoint = randomize_endpoint
        self.pythonic_params = pythonic_params

        self.request_body = None
        self.parameters = list(self.resolve_parameters(operation.get('parameters', [])))
        if path_parameters:
            self.parameters += list(self.resolve_parameters(path_parameters))

        self.security = operation.get('security', app_security)
        self.produces = operation.get('produces', app_produces)
        self.consumes = operation.get('consumes', app_consumes)
        
        logger.debug('consumes: %s' % self.consumes)
        logger.debug('produces: %s' % self.produces)

        resolution = resolver.resolve(self)
        self.operation_id = resolution.operation_id
        self._undecorated_function = resolution.function

        self.validate_defaults()

    def validate_defaults(self):
        for param_defn in self.parameters:
            try:
                if param_defn['in'] == 'query' and 'default' in param_defn:
                    validation.validate_type(param_defn, param_defn['default'],
                                             'query', param_defn['name'])
            except (TypeValidationError, ValidationError):
                raise InvalidSpecification('The parameter \'{param_name}\' has a default value which is not of'
                                           ' type \'{param_type}\''.format(param_name=param_defn['name'],
                                                                           param_type=param_defn['type']))

    def get_path_parameter_types(self):
        types = {}
        path_parameters = (p for p in self.parameters if p["in"] == "path")
        for path_defn in path_parameters:
            if path_defn.get('type') == 'string' and path_defn.get('format') == 'path':
                # path is special case for type 'string'
                path_type = 'path'
            else:
                path_type = path_defn.get('type')
            types[path_defn['name']] = path_type
        return types

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
        if "schema" in schema:
            schema['schema']['definitions'] = self.definitions

        return schema



