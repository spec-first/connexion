import logging
from copy import deepcopy

from jsonschema import ValidationError

from connexion.operations.abstract import AbstractOperation

from ..decorators.response import ResponseValidator
from ..decorators.validation import (RequestBodyValidator,
                                     Swagger2ParameterValidator,
                                     TypeValidationError)
from ..exceptions import InvalidSpecification
from ..utils import deep_get, is_null, is_nullable, make_type

logger = logging.getLogger("connexion.operations.swagger2")

VALIDATOR_MAP = {
    'parameter': Swagger2ParameterValidator,
    'body': RequestBodyValidator,
    'response': ResponseValidator,
}


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

        self._validator_map = dict(VALIDATOR_MAP)
        self._validator_map.update(validator_map or {})

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
            pythonic_params=pythonic_params
        )

        self._produces = operation.get('produces', app_produces)
        self._consumes = operation.get('consumes', app_consumes)

        self.definitions = definitions or {}

        self.definitions_map = {
            'definitions': self.definitions,
            'parameters': parameter_definitions,
            'responses': response_definitions
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

        logger.error('consumes: %s', self.consumes)
        logger.error('produces: %s', self.produces)

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
                    self.validate_type(param_defn, param_defn['default'],
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

    def response_definition(self, status_code=None, content_type=None):
        content_type = content_type or self.get_mimetype()
        response_definitions = self._responses
        response_definition = response_definitions.get(str(status_code), response_definitions.get("default", {}))
        response_definition = self._resolve_reference(response_definition)
        return response_definition

    def response_schema(self, status_code=None, content_type=None):
        response_definition = self.response_definition(status_code, content_type)
        return self._resolve_reference(response_definition.get("schema", {}))

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

    def get_arguments(self, path_params, query_params, body, files, arguments,
                      has_kwargs, sanitize):
        """
        get arguments for handler function
        """
        ret = {}
        ret.update(self._get_path_arguments(path_params, sanitize))
        ret.update(self._get_query_arguments(query_params, arguments, has_kwargs, sanitize))
        ret.update(self._get_body_argument(body, arguments, has_kwargs, sanitize))
        ret.update(self._get_file_arguments(files, arguments, has_kwargs))
        return ret

    def _get_query_arguments(self, query, arguments, has_kwargs, sanitize):
        query_defns = {sanitize(p["name"]): p
                       for p in self.parameters
                       if p["in"] == "query"}
        default_query_params = {k: v['default']
                                for k, v in query_defns.items()
                                if 'default' in v}
        query_arguments = deepcopy(default_query_params)

        logger.error(query)

        request_query = {}
        for k, values in query.items():
            k = sanitize(k)
            query_defn = query_defns.get(k, None)
            query_schema = query_defn
            if (query_schema is not None and query_schema['type'] == 'array'):
                request_query[k] = self._resolve_query_duplicates(values, query_defn)
            else:
                request_query[k] = values[-1]

        query_arguments.update(request_query)
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

    def _get_body_argument(self, body, arguments, has_kwargs, sanitize):
        kwargs = {}
        body_parameters = [p for p in self.parameters if p['in'] == 'body'] or [{}]
        default_body = body_parameters[0].get('schema', {}).get('default')
        body_name = sanitize(body_parameters[0].get('name'))

        body = body or default_body

        form_defns = {sanitize(p['name']): p
                      for p in self.parameters
                      if p['in'] == 'formData'}

        default_form_params = {sanitize(p['name']): p['default']
                               for p in form_defns
                               if 'default' in p}

        # Add body parameters
        if body_name:
            if not has_kwargs and body_name not in arguments:
                logger.debug("Body parameter '%s' not in function arguments", body_name)
            else:
                logger.debug("Body parameter '%s' in function arguments", body_name)
                kwargs[body_name] = body

        # Add formData parameters
        form_arguments = deepcopy(default_form_params)
        if form_defns and body:
            form_arguments.update(body)
        for key, value in form_arguments.items():
            if not has_kwargs and key not in arguments:
                logger.debug("FormData parameter '%s' not in function arguments", key)
            else:
                logger.debug("FormData parameter '%s' in function arguments", key)
                try:
                    form_defn = form_defns[key]
                except KeyError:  # pragma: no cover
                    logger.error("Function argument '{}' not defined in specification".format(key))
                else:
                    kwargs[key] = self._get_val_from_param(value, form_defn)
        return kwargs

    @staticmethod
    def _resolve_query_duplicates(values, param_defn):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the last-defined value.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "4,5,6".
            However, if 'collectionFormat' is 'multi' then the duplicate values
            are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get('collectionFormat') == 'multi':
            return ','.join(values)
        # default to last defined value
        return values[-1]

    @staticmethod
    def query_split(value, param_defn):
        if param_defn.get("collectionFormat") == 'pipes':
            return value.split('|')
        return value.split(',')

    def _get_val_from_param(self, value, query_defn):
        if is_nullable(query_defn) and is_null(value):
            return None

        query_schema = query_defn

        if query_schema["type"] == "array":  # then logic is more complex
            parts = self.query_split(value, query_defn)
            return [make_type(part, query_defn["items"]["type"]) for part in parts]
        else:
            return make_type(value, query_defn["type"])

    @staticmethod
    def validate_type(param_defn, value, parameter_type, parameter_name=None):
        # XXX DGK - figure out how to decouple this
        param_schema = param_defn
        param_type = param_schema.get('type')
        parameter_name = parameter_name or param_defn['name']
        if param_type == 'array':
            parts = Swagger2Operation.query_split(value, param_defn)
            converted_parts = []
            for part in parts:
                try:
                    converted = make_type(part, param_schema['items']['type'])
                except (ValueError, TypeError):
                    converted = part
                converted_parts.append(converted)
            return converted_parts
        else:
            try:
                return make_type(value, param_type)
            except ValueError:
                raise TypeValidationError(param_type, parameter_type, parameter_name)
            except TypeError:
                return value
