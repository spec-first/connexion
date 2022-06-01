import abc
import functools
import logging
import pathlib
import typing as t

from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Scope, Receive, Send
from connexion.apis.abstract import AbstractSpecAPI
from connexion.decorators.uri_parsing import AbstractURIParser, OpenAPIURIParser, Swagger2URIParser

from connexion.exceptions import MissingMiddleware, InvalidSpecification
from connexion.http_facts import METHODS
from connexion.lifecycle import MiddlewareRequest
from connexion.middleware import AppMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from connexion.decorators.produces import BaseSerializer, Produces
from connexion.decorators.response import ResponseValidator
from connexion.decorators.validation import ParameterValidator, RequestBodyValidator
from connexion.operations.abstract import DEFAULT_MIMETYPE
from connexion.utils import all_json, is_nullable


logger = logging.getLogger("connexion.middleware.validation")


VALIDATOR_MAP = {
    'parameter': ParameterValidator,
    'body': RequestBodyValidator,
    # 'response': ResponseValidator,
}


# TODO: split up Request parsing/validation and response parsing/validation?
#   response validation as separate middleware to allow easy decoupling and disabling/enabling?
class ValidationMiddleware(AppMiddleware):
    """Middleware for validating requests according to the API contract."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, ValidationAPI] = {}

    def add_api(self, specification: t.Union[pathlib.Path, str, dict], **kwargs) -> None:
        api = ValidationAPI(specification, **kwargs)
        self.apis[api.base_path] = api

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            connexion_context = scope['extensions'][ROUTING_CONTEXT]
        except KeyError:
            raise MissingMiddleware('Could not find routing information in scope. Please make sure '
                                    'you have a routing middleware registered upstream. ')

        api_base_path = connexion_context.get('api_base_path')
        if api_base_path:
            api = self.apis[api_base_path]
            operation_id = connexion_context.get('operation_id')
            try:
                operation = api.operations[operation_id]
            except KeyError as e:
                raise ValueError('Encountered unknown operation_id.') from e
            else:
                # TODO: Change because we need access to the request body and response body/headers
                request = MiddlewareRequest(scope, receive, send)
                await operation(request)


class ValidationAPI(AbstractSpecAPI):

    def __init__(
        self,
        specification,
        base_path=None,
        arguments=None,
        validate_responses: bool = False,
        strict_validation: bool = False,
        resolver=None,
        debug=False,
        resolver_error_handler=None,
        validator_map: dict = None,
        pythonic_params=False,
        pass_context_arg_name=None,
        options=None,
        uri_parser_class=None,
        **kwargs
    ) -> None:
        self.validator_map = validator_map

        logger.debug('Validate Responses: %s', str(validate_responses))
        self.validate_responses = validate_responses

        logger.debug('Strict Request Validation: %s', str(strict_validation))
        self.strict_validation = strict_validation

        logger.debug('Pythonic params: %s', str(pythonic_params))
        self.pythonic_params = pythonic_params

        self.uri_parser_class = uri_parser_class

        super().__init__(specification, base_path=base_path, arguments=arguments,
                         resolver=resolver, resolver_error_handler=resolver_error_handler,
                         debug=debug, pass_context_arg_name=pass_context_arg_name, options=options)

        self.operations: t.Dict[str, AbstractValidationOperation] = {}

        self.add_paths()

    def add_paths(self):
        paths = self.specification.get('paths', {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method not in METHODS:
                    continue
                operation_id = operation.get('operationId')
                if operation_id:
                    self.operations[operation_id] = self.make_operation(operation)

    def make_operation(self, operation_spec: dict = None):
        if self.specification.version < (3, 0, 0):
            return Swagger2ValidationOperation(
                api=self,
                app_consumes=[],
                app_produces=[],
                operation=operation_spec,
                strict_validation=self.strict_validation,
                validator_map=self.validator_map,
                uri_parser_class=self.uri_parser_class,
            )
        else:
            return OpenAPIValidationOperation(
                api=self,
                operation=operation_spec,
                strict_validation=self.strict_validation,
                validator_map=self.validator_map,
                uri_parser_class=self.uri_parser_class,
            )

class AbstractValidationOperation:
    def __init__(
            self,
            api,
            operation,
            strict_validation=False,
            validator_map: t.Optional[dict] = None,
            uri_parser_class: t.Optional[t.Type[AbstractURIParser]] = None,
    ) -> None:
        self._api = api

        logger.debug('Strict Request Validation: %s', str(strict_validation))
        self._strict_validation = strict_validation

        self._uri_parser_class = uri_parser_class

        self._validator_map = dict(VALIDATOR_MAP)
        self._validator_map.update(validator_map or {})

        self._validation_fn = self._get_validation_fn()

    @property
    def api(self):
        return self._api

    # TODO: Remove properties and use ordinary attributes?
    @property
    def validator_map(self):
        """
        Validators to use for parameter, body, and response validation
        """
        return self._validator_map

    @property
    def strict_validation(self):
        """
        If True, validate all requests against the spec
        """
        return self._strict_validation

    def _get_validation_fn(self):
        async def function(request):
            return request

        # produces_decorator = self.__content_type_decorator
        # logger.debug('... Adding produces decorator (%r)', produces_decorator)
        # function = produces_decorator(function)

        for validation_decorator in self.__validation_decorators:
            function = validation_decorator(function)

        return function

    # @staticmethod
    # def _get_file_arguments(files, arguments, has_kwargs=False):
    #     return {k: v for k, v in files.items() if k in arguments or has_kwargs}

    @abc.abstractmethod
    def _get_val_from_param(self, value, query_defn):
        """
        Convert input parameters into the correct type
        """

    @property
    @abc.abstractmethod
    def parameters(self):
        """
        Returns the parameters for this operation
        """

    # @property
    # @abc.abstractmethod
    # def produces(self):
    #     """
    #     Content-Types that the operation produces
    #     """

    # @property
    # @abc.abstractmethod
    # def consumes(self):
    #     """
    #     Content-Types that the operation consumes
    #     """

    @property
    @abc.abstractmethod
    def body_schema(self):
        """
        The body schema definition for this operation.
        """

    @property
    @abc.abstractmethod
    def body_definition(self):
        """
        The body definition for this operation.
        :rtype: dict
        """

    def response_definition(self, status_code=None,
                            content_type=None):
        """
        response definition for this endpoint
        """
        content_type = content_type or self.get_mimetype()
        response_definition = self.responses.get(
            str(status_code),
            self.responses.get("default", {})
        )
        return response_definition

    @abc.abstractmethod
    def response_schema(self, status_code=None, content_type=None):
        """
        response schema for this endpoint
        """

    @abc.abstractmethod
    def get_path_parameter_types(self):
        """
        Returns the types for parameters in the path
        """

    @abc.abstractmethod
    def with_definitions(self, schema):
        """
        Returns the given schema, but with the definitions from the spec
        attached. This allows any remaining references to be resolved by a
        validator (for example).
        """

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
    def _uri_parsing_decorator(self):
        """
        Returns a decorator that parses request data and handles things like
        array types, and duplicate parameter definitions.
        """
        return self._uri_parser_class(self.parameters, self.body_definition)

    async def __call__(self, request: MiddlewareRequest):
        return await self._validation_fn(request)

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
                                     strict_validation=self.strict_validation)
        if self.body_schema:
            yield RequestBodyValidator(self.body_schema, self.consumes, None,
                                       is_nullable(self.body_definition),
                                       strict_validation=self.strict_validation)

    def json_loads(self, data):
        """
        A wrapper for calling the API specific JSON loader.

        :param data: The JSON data in textual form.
        :type data: bytes
        """
        return self.api.json_loads(data)


class Swagger2ValidationOperation(AbstractValidationOperation):

    def __init__(
        self,
        api,
        operation,
        app_consumes,
        app_produces,
        strict_validation=False,
        validator_map: t.Optional[dict] = None,
        uri_parser_class: t.Optional[t.Type[AbstractURIParser]] = None,
        # TODO: rename to operation_parameters?
        path_parameters: t.Optional[t.List[dict]] = None,
        definitions: t.Optional[dict] = None,
    ) -> None:
        uri_parser_class = uri_parser_class or Swagger2URIParser

        # TODO: override?
        #    "These parameters can be overridden at the operation level,
        #       but cannot be removed there."
        self._parameters = operation.get('parameters', [])
        if path_parameters:
            self._parameters += path_parameters

        self.definitions = definitions or {}
        
        self._produces = operation.get('produces', app_produces)
        self._consumes = operation.get('consumes', app_consumes)

        super().__init__(
            api=api,
            operation=operation,
            strict_validation=strict_validation,
            validator_map=validator_map,
            uri_parser_class=uri_parser_class,
        )

    @property
    def parameters(self):
        return self._parameters

    @property
    def consumes(self):
        return self._consumes

    @property
    def produces(self):
        return self._produces

    def with_definitions(self, schema):
        if "schema" in schema:
            schema['schema']['definitions'] = self.definitions
        return schema

    def response_schema(self, status_code=None, content_type=None):
        response_definition = self.response_definition(
            status_code, content_type
        )
        return self.with_definitions(response_definition.get("schema", {}))

    @property
    def body_schema(self):
        """
        The body schema definition for this operation.
        """
        return self.with_definitions(self.body_definition).get('schema', {})

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


class OpenAPIValidationOperation(AbstractValidationOperation):

    def __init__(
        self,
        api,
        operation,
        strict_validation=False,
        validator_map: t.Optional[dict] = None,
        uri_parser_class: t.Optional[t.Type[AbstractURIParser]] = None,
        path_parameters: t.Optional[t.List[dict]] = None,
    ) -> None:
        uri_parser_class = uri_parser_class or OpenAPIURIParser

        self._parameters = operation.get('parameters', [])
        if path_parameters:
            self._parameters += path_parameters

        super().__init__(
            api=api,
            operation=operation,
            strict_validation=strict_validation,
            validator_map=validator_map,
            uri_parser_class=uri_parser_class
        )

    @property
    def request_body(self):
        return self._request_body

    # @property
    # def parameters(self):
    #     return self._parameters

    # @property
    # def consumes(self):
    #     return self._consumes

    # @property
    # def produces(self):
    #     return self._produces

    def with_definitions(self, schema):
        if self.components:
            schema['schema']['components'] = self.components
        return schema

    def response_schema(self, status_code=None, content_type=None):
        response_definition = self.response_definition(
            status_code, content_type
        )
        content_definition = response_definition.get("content", response_definition)
        content_definition = content_definition.get(content_type, content_definition)
        if "schema" in content_definition:
            return self.with_definitions(content_definition).get("schema", {})
        return {}

    @property
    def body_schema(self):
        """
        The body schema definition for this operation.
        """
        return self.body_definition.get('schema', {})

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
            return self.with_definitions(res)
        return {}


class MissingValidationOperation(Exception):
    """Missing validation operation exception."""
