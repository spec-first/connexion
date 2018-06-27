import logging
from copy import deepcopy

from jsonschema import ValidationError

from connexion.operations.abstract import AbstractOperation

from ..decorators import validation
from ..decorators.validation import TypeValidationError
from ..exceptions import InvalidSpecification
from ..utils import deep_get

logger = logging.getLogger("connexion.operations.swagger2")


class Swagger2Operation(AbstractOperation):

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
        app_security = operation.get('security', app_security)

        super(Swagger2Operation, self).__init__(
            api=api,
            method=method,
            path=path,
            operation=operation,
            resolver=resolver,
            app_security=app_security,
            security_schemes=security_definitions,
            validate_responses=validate_responses,
            strict_validation=strict_validation,
            randomize_endpoint=randomize_endpoint,
            pythonic_params=pythonic_params,
            validator_map=validator_map
        )

        self._produces = operation.get('produces', app_produces)
        self._consumes = operation.get('consumes', app_consumes)

        self.definitions = definitions or {}
        self.parameter_definitions = parameter_definitions
        self.response_definitions = response_definitions

        self.definitions_map = {
            'definitions': self.definitions,
            'parameters': self.parameter_definitions,
            'responses': self.response_definitions
        }

        def resolve_parameters(parameters):
            return [self._resolve_reference(p) for p in parameters]

        self.parameters = resolve_parameters(operation.get('parameters', []))
        if path_parameters:
            self.parameters += resolve_parameters(path_parameters)

        def resolve_responses(responses):
            if not responses:
                return {}
            for status_code, resp in responses.items():
                if not resp:
                    continue

                # check definitions
                if '$ref' in resp:
                    ref = self._resolve_reference(resp)
                    del resp['$ref']
                    resp = ref

                examples = resp.get("examples", {})
                ref = self._resolve_reference(examples)
                if ref:
                    resp["examples"] = ref

                schema = resp.get("schema", {})
                ref = self._resolve_reference(schema)
                if ref:
                    resp["schema"] = ref

            return responses

        self._responses = resolve_responses(operation.get('responses', {}))
        logger.debug(self._responses)

        logger.debug('consumes: %s', self.consumes)
        logger.debug('produces: %s', self.produces)

        self._validate_defaults()

    @property
    def _spec_definitions(self):
        return self.definitions_map

    @property
    def consumes(self):
        return self._consumes

    @property
    def produces(self):
        return self._produces

    def _validate_defaults(self):
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

    def _resolve_reference(self, schema):
        schema = deepcopy(schema)  # avoid changing the original schema
        self._check_references(schema)

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

    def example_response(self, code=None, *args, **kwargs):
        """
        Returns example response from spec
        """
        # simply use the first/lowest status code, this is probably 200 or 201
        try:
            code = code or sorted(self._responses.keys())[0]
        except IndexError:
            code = 200
        examples_path = [str(code), 'examples']
        schema_example_path = [str(code), 'schema', 'example']
        try:
            code = int(code)
        except ValueError:
            code = 200
        try:
            return (list(deep_get(self._responses, examples_path).values())[0], code)
        except KeyError:
            pass
        try:
            return (deep_get(self._responses, schema_example_path), code)
        except KeyError:
            return (None, code)

    @property
    def body_schema(self):
        """
        The body schema definition for this operation.
        """
        return self._resolve_reference(self.body_definition.get('schema', {}))

    @property
    def body_definition(self):
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**

        :rtype: dict
        """
        body_parameters = [p for p in self.parameters if p['in'] == 'body']
        if len(body_parameters) > 1:
            raise InvalidSpecification(
                "{method} {path} There can be one 'body' parameter at most".format(
                    method=self.method,
                    path=self.path))
        return body_parameters[0] if body_parameters else {}
