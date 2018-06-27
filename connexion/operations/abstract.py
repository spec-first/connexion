import abc
import logging

import six

from connexion.operations.secure import SecureOperation

from ..decorators.metrics import UWSGIMetricsCollector
from ..decorators.parameter import parameter_to_arg
from ..decorators.produces import BaseSerializer, Produces
from ..decorators.response import ResponseValidator
from ..decorators.validation import ParameterValidator, RequestBodyValidator
from ..exceptions import InvalidSpecification

from ..utils import all_json, deep_get, is_nullable

logger = logging.getLogger('connexion.operations.abstract')

DEFAULT_MIMETYPE = 'application/json'

VALIDATOR_MAP = {
    'parameter': ParameterValidator,
    'body': RequestBodyValidator,
    'response': ResponseValidator,
}


@six.add_metaclass(abc.ABCMeta)
class AbstractOperation(SecureOperation):
    """ What is an Operation?
        An API routes requests to the operation by a (path, method) pair.
        The operation uses a resolver to resolve its handler function.
        We use the provided spec to do a bunch of heavy lifting before
        (and after) we call security_schemes handler.
        What heavy lifting?
        - on creation:
          - validate defaults
          - resolve references to components / definitions
        - at runtime:
          - secure endpoint
          - validate inputs
          - convert "web inputs" (request bodies, query parameters, etc) into _function inputs_
          - convert "funtion outputs" into _web outputs_
          - validate outputs
        This leaves the handler function to implement the business logic, and do away with the
        boilerplate.

        An operation needs a way to:
         - wrap a handler function
         - a security wrapper

    """
    def __init__(self, api, method, path, operation, resolver,
                 app_security=None, security_schemes=None,
                 validate_responses=False, strict_validation=False,
                 randomize_endpoint=None, pythonic_params=False,
                 validator_map=None):
        """
        """
        self._api = api
        self._method = method
        self._path = path
        self._operation = operation
        self._resolver = resolver
        self._security = app_security
        self._security_schemes = security_schemes
        self._validate_responses = validate_responses
        self._strict_validation = strict_validation
        self._pythonic_params = pythonic_params
        self._randomize_endpoint = randomize_endpoint

        self._validator_map = dict(VALIDATOR_MAP)
        self._validator_map.update(validator_map or {})

        self._router_controller = self._operation.get('x-swagger-router-controller')

        self._operation_id = self._operation.get("operationId")
        self._resolution = resolver.resolve(self)
        self._operation_id = self._resolution.operation_id

    @property
    def method(self):
        """
        The HTTP method for this operation (ex. GET, POST)
        """
        return self._method

    @property
    def path(self):
        """
        The path of the operation, relative to the API base path
        """
        return self._path

    @property
    def validator_map(self):
        """
        Validators to use for parameter, body, and response validation
        """
        return self._validator_map

    @property
    def operation_id(self):
        """
        The operation id used to indentify the operation internally to the app
        """
        return self._operation_id

    @property
    def randomize_endpoint(self):
        """
        number of random digits to generate and append to the operation_id.
        """
        return self._randomize_endpoint

    @property
    def router_controller(self):
        """
        The router controller to use (python module where handler functions live)
        """
        return self._router_controller

    @property
    def strict_validation(self):
        """
        If True, validate all requests against the spec
        """
        return False

    @abc.abstractproperty
    def produces(self):
        """
        Content-Types that the operation produces
        """
        return []

    @abc.abstractproperty
    def consumes(self):
        """
        Content-Types that the operation consumes
        """
        return []

    @abc.abstractproperty
    def _spec_definitions(self):
        """
        a nested dictionary that is used by _resolve_reference.
        It contains the definitions referenced in the spec.

        for example, a spec with "#/components/schemas/Banana"
        would have a definitions map that looked like:
        {"components": {"schemas": {"Banana": {...}}}}
        """
        return {}

    @abc.abstractproperty
    def body_schema(self):
        """
        The body schema definition for this operation.
        """

    @abc.abstractproperty
    def body_definition(self):
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**

        :rtype: dict
        """

    @property
    def pythonic_params(self):
        """
        """

    @property
    def validate_responses(self):
        """
        """

    @abc.abstractmethod
    def example_response(self, code='default', mimetype=None):
        """
        Returns an example from the spec
        """

    @abc.abstractmethod
    def get_path_parameter_types(self):
        """
        Returns the types for parameters in the path
        """

    @abc.abstractmethod
    def _validate_defaults(self):
        """
        validate the openapi operation defaults using the openapi schema
        """

    @abc.abstractmethod
    def _resolve_reference(self, schema):
        """
        replaces schema references like "#/components/schemas/MySchema"
        with the contents of that reference.

        relies on self._components to be a nested dictionary with the
        definitions for all of the components.

        See helper methods _check_references and _retrieve_reference
        """

    def _check_references(self, schema):
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
                "{method} {path} '$ref' needs to start with '#/'".format(
                    method=self.method,
                    path=self.path))
        path = reference[2:].split('/')
        try:
            definition = deep_get(self._spec_definitions, path)
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

    @property
    def function(self):
        """
        Operation function with decorators

        :rtype: types.FunctionType
        """

        # XXX DGK
        function = parameter_to_arg(
            self.parameters, self.body_schema, self.consumes, self._resolution.function,
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
