import logging
from copy import deepcopy

from jsonschema import ValidationError

from connexion.operations.abstract import AbstractOperation

from ..decorators.response import ResponseValidator
from ..decorators.validation import (OpenAPIParameterValidator,
                                     RequestBodyValidator, TypeValidationError)
from ..decorators.uri_parsing import OpenAPIURIParser
from ..exceptions import InvalidSpecification
from ..utils import deep_get, is_null, is_nullable, make_type

logger = logging.getLogger("connexion.operations.openapi3")

QUERY_STRING_DELIMITERS = {
    'spaceDelimited': ' ',
    'pipeDelimited': '|',
    'simple': ',',
    'form': ','
}

VALIDATOR_MAP = {
    'parameter': OpenAPIParameterValidator,
    'body': RequestBodyValidator,
    'response': ResponseValidator,
}


class OpenAPIOperation(AbstractOperation):

    """
    A single API operation on a path.
    """

    def __init__(self, api, method, path, operation, resolver, path_parameters=None,
                 app_security=None, components=None, validate_responses=False,
                 strict_validation=False, randomize_endpoint=None, validator_map=None,
                 pythonic_params=False):
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
        """
        self.components = components or {}

        def component_get(oas3_name):
            return self.components.get(oas3_name, {})

        # operation overrides globals
        security_schemes = component_get('securitySchemes')
        app_security = operation.get('security', app_security)

        self._validator_map = dict(VALIDATOR_MAP)
        self._validator_map.update(validator_map or {})

        super(OpenAPIOperation, self).__init__(
            api=api,
            method=method,
            path=path,
            operation=operation,
            resolver=resolver,
            app_security=app_security,
            security_schemes=security_schemes,
            validate_responses=validate_responses,
            strict_validation=strict_validation,
            randomize_endpoint=randomize_endpoint,
            pythonic_params=pythonic_params,
        )

        self._definitions_map = {
            'components': {
                'schemas': component_get('schemas'),
                'requestBodies': component_get('requestBodies'),
                'parameters': component_get('parameters'),
                'securitySchemes': component_get('securitySchemes'),
                'responses': component_get('responses'),
                'headers': component_get('headers'),
            }
        }

        # todo support definition references
        # todo support references to application level parameters
        self._request_body = operation.get('requestBody')
        if self._request_body:
            self._request_body = self._resolve_reference(self._request_body)

        def resolve_parameters(parameters):
            return [self._resolve_reference(p) for p in parameters]

        self.parameters = resolve_parameters(operation.get('parameters', []))
        if path_parameters:
            self.parameters += resolve_parameters(path_parameters)

        def resolve_responses(responses):
            if not responses:
                return responses
            responses = deepcopy(responses)
            for status_code, resp in responses.items():
                # check components/responses
                if '$ref' in resp:
                    ref = self._resolve_reference(resp)
                    del resp['$ref']
                    resp = ref

                content = resp.get("content", {})
                for mimetype, resp in content.items():
                    # check components/examples
                    examples = resp.get("examples", [])
                    for example in examples:
                        example = self._resolve_reference(example)

                    example = resp.get("example", {})
                    ref = self._resolve_reference(example)
                    if ref:
                        resp["example"] = ref

                    schema = resp.get("schema", {})
                    ref = self._resolve_reference(schema)
                    if ref:
                        resp["schema"] = ref

            return responses

        self._responses = resolve_responses(operation.get('responses', {}))

        # TODO figure out how to support multiple mimetypes
        # NOTE we currently just combine all of the possible mimetypes,
        #      but we need to refactor to support mimetypes by response code
        response_codes = operation.get('responses', {})
        response_content_types = []
        for _, defn in response_codes.items():
            response_content_types += defn.get('content', {}).keys()
        self._produces = response_content_types or ['application/json']

        request_content = operation.get('requestBody', {}).get('content', {})
        self._consumes = list(request_content.keys()) or ['application/json']

        logger.debug('consumes: %s' % self.consumes)
        logger.debug('produces: %s' % self.produces)

        self._validate_defaults()

    @property
    def request_body(self):
        return self._request_body

    @property
    def consumes(self):
        return self._consumes

    @property
    def produces(self):
        return self._produces

    @property
    def _spec_definitions(self):
        return self._definitions_map

    def _validate_defaults(self):
        validator = self.validator_map["parameter"]
        for param_defn in self.parameters:
            try:
                param_schema = param_defn["schema"]
                if param_defn['in'] == 'query' and 'default' in param_schema:
                    validator.validate_type(param_defn, param_schema['default'],
                                            'query', param_defn['name'])
            except (TypeValidationError, ValidationError):
                raise InvalidSpecification('The parameter \'{param_name}\' has a default value which is not of'
                                           ' type \'{param_type}\''.format(param_name=param_defn['name'],
                                                                           param_type=param_schema['type']))

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

        # if the schema includes allOf or oneOf or anyOf
        for multi in ['allOf', 'anyOf', 'oneOf']:
            upd = []
            for s in schema.get(multi, []):
                upd.append(self._resolve_reference(s))
            if upd:
                schema[multi] = upd

        # additionalProperties
        try:
            ap = schema['additionalProperties']
            if ap:
                schema['additionalProperties'] = self._resolve_reference(ap)
        except KeyError:
            pass

        # if there is a schema object on this param or response, then we just
        # need to include the defs and it can be validated by jsonschema
        if "$ref" in schema.get("schema", {}):
            if self.components:
                schema['schema']['components'] = self.components
            return schema

        return schema

    def response_definition(self, status_code=None, content_type=None):
        content_type = content_type or self.get_mimetype()
        response_definitions = self._responses
        response_definition = response_definitions.get(str(status_code), response_definitions.get("default", {}))
        response_definition = self._resolve_reference(response_definition)
        return response_definition

    def response_schema(self, status_code=None, content_type=None):
        response_definition = self.response_definition(status_code, content_type)
        content_definition = response_definition.get("content", response_definition)
        content_definition = content_definition.get(content_type, content_definition)
        return self._resolve_reference(content_definition.get("schema", {}))

    def example_response(self, code=None, content_type=None):
        """
        Returns example response from spec
        """
        # simply use the first/lowest status code, this is probably 200 or 201
        try:
            code = code or sorted(self._responses.keys())[0]
        except IndexError:
            code = 200

        content_type = content_type or self.get_mimetype()
        examples_path = [str(code), 'content', content_type, 'examples']
        example_path = [str(code), 'content', content_type, 'example']
        schema_example_path = [str(code), 'content', content_type, 'schema', 'example']

        try:
            code = int(code)
        except ValueError:
            code = 200
        try:
            return (deep_get(self._responses, examples_path)[0], code)
        except (KeyError, IndexError):
            pass
        try:
            return (deep_get(self._responses, example_path), code)
        except KeyError:
            pass
        try:
            return (deep_get(self._responses, schema_example_path), code)
        except KeyError:
            return (None, code)

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
        return self._resolve_reference(self.body_definition.get('schema', {}))

    @property
    def body_definition(self):
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**

        :rtype: dict
        """
        if self._request_body:
            if len(self.consumes) > 1:
                logger.warning(
                    'this operation accepts multiple content types, using %s',
                    self.consumes[0])
            res = self._request_body.get('content', {}).get(self.consumes[0], {})
            return self._resolve_reference(res)
        return {}

    @property
    def _query_parsing_decorator(self):
        return OpenAPIURIParser({p["name"]: p for p in self.parameters if p["in"] in ["query", "path"]})

    def _get_body_argument(self, body, arguments, has_kwargs):
        body_schema = self.body_schema
        default_body = body_schema.get('default')
        body = body or default_body
        if body_schema:
            x_body_name = body_schema.get('x-body-name', 'body')
            logger.debug('x-body-name is %s' % x_body_name)
            if x_body_name in arguments or has_kwargs:
                return {x_body_name: body}
        return {}

    def get_arguments(self, path_params, query_params, body, files, arguments,
                      has_kwargs, sanitize):
        """
        get arguments for handler function
        """
        ret = {}
        ret.update(self._get_path_arguments(path_params, sanitize))
        ret.update(self._get_query_arguments(query_params, arguments, has_kwargs, sanitize))
        ret.update(self._get_body_argument(body, arguments, has_kwargs))
        ret.update(self._get_file_arguments(files, arguments, has_kwargs))
        return ret

    def _get_query_arguments(self, query, arguments, has_kwargs, sanitize):
        query_defns = {sanitize(p["name"]): p
                       for p in self.parameters
                       if p["in"] == "query"}
        default_query_params = {k: v["schema"]['default']
                                for k, v in query_defns.items()
                                if 'default' in v["schema"]}
        query_arguments = deepcopy(default_query_params)

        query_arguments.update(query)
        res = {}
        for key, value in query_arguments.items():
            key = sanitize(key)
            if not has_kwargs and key not in arguments:
                logger.debug("Query Parameter '%s' not in function arguments", key)
            else:
                logger.debug("Query Parameter '%s' in function arguments", key)
                try:
                    query_defn = query_defns[key]
                except KeyError:  # pragma: no cover
                    logger.error("Function argument '{}' not defined in specification".format(key))
                else:
                    logger.debug('%s is a %s', key, query_defn)
                    res[key] = self._get_val_from_param(value, query_defn)
        return res

    def _get_val_from_param(self, value, query_defn):
        if is_nullable(query_defn) and is_null(value):
            return None

        query_schema = query_defn["schema"]

        if query_schema["type"] == "array":
            return [make_type(part, query_schema["items"]["type"]) for part in value]
        else:
            return make_type(value, query_schema["type"])
