"""
Validation Middleware.
"""
import functools
import logging
import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import ImmutableMultiDict, UploadFile

from connexion.apis.abstract import AbstractSpecAPI
from connexion.decorators.uri_parsing import AbstractURIParser, Swagger2URIParser, OpenAPIURIParser
from connexion.exceptions import MissingMiddleware, ResolverError
from connexion.http_facts import METHODS
from connexion.lifecycle import ConnexionRequest, MiddlewareRequest
from connexion.middleware import AppMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from connexion.operations import AbstractOperation, OpenAPIOperation, Swagger2Operation

from ..decorators.response import ResponseValidator
from ..decorators.validation import ParameterValidator, RequestBodyValidator

logger = logging.getLogger("connexion.middleware.validation")

VALIDATOR_MAP = {
    "parameter": ParameterValidator,
    "body": RequestBodyValidator,
    "response": ResponseValidator,
}


# TODO: split up Request parsing/validation and response parsing/validation?
#   response validation as separate middleware to allow easy decoupling and disabling/enabling?
class ValidationMiddleware(AppMiddleware):

    """Middleware for validating requests according to the API contract."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, ValidationAPI] = {}

    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        api = ValidationAPI(specification, **kwargs)
        self.apis[api.base_path] = api

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            connexion_context = scope["extensions"][ROUTING_CONTEXT]
        except KeyError:
            raise MissingMiddleware(
                "Could not find routing information in scope. Please make sure "
                "you have a routing middleware registered upstream. "
            )
        api_base_path = connexion_context.get("api_base_path")
        if api_base_path:
            api = self.apis[api_base_path]
            operation_id = connexion_context.get("operation_id")
            try:
                operation = api.operations[operation_id]
            except KeyError as e:
                if operation_id is None:
                    logger.debug("Skipping validation check for operation without id.")
                    await self.app(scope, receive, send)
                    return
                else:
                    raise MissingValidationOperation(
                        "Encountered unknown operation_id."
                    ) from e
            else:
                # TODO: Add validation logic
                # messages = []
                # async def wrapped_receive():
                #     msg = await receive()
                #     messages.append(msg)
                #     return msg
                # request = MiddlewareRequest(scope, wrapped_receive)
                # if messages:
                #     async def new_receive():
                #         msg = messages.pop(0)
                #         return msg
                # else:
                #     new_receive = receive

                # await operation(request)
                # await self.app(scope, new_receive, send)
                await self.app(scope, receive, send)

        else:
            await self.app(scope, receive, send)


class ValidationAPI(AbstractSpecAPI):
    """Validation API."""

    def __init__(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        *args,
        validate_responses=False,
        strict_validation=False,
        validator_map=None,
        uri_parser_class=None,
        **kwargs,
    ):
        super().__init__(specification, *args, **kwargs)

        self.validator_map = validator_map

        logger.debug("Validate Responses: %s", str(validate_responses))
        self.validate_responses = validate_responses

        logger.debug("Strict Request Validation: %s", str(strict_validation))
        self.strict_validation = strict_validation

        self.uri_parser_class = uri_parser_class

        self.operations: t.Dict[str, AbstractValidationOperation] = {}
        self.add_paths()

    def add_paths(self):
        paths = self.specification.get("paths", {})
        for path, methods in paths.items():
            for method in methods:
                if method not in METHODS:
                    continue
                try:
                    self.add_operation(path, method)
                except ResolverError:
                    # ResolverErrors are either raised or handled in routing middleware.
                    pass

    def add_operation(self, path: str, method: str) -> None:
        operation_cls = self.specification.operation_cls
        operation = operation_cls.from_spec(
            self.specification, self, path, method, self.resolver
        )
        validation_operation = self.make_operation(operation)
        self._add_operation_internal(operation.operation_id, validation_operation)

    def make_operation(self, operation: AbstractOperation):
        if isinstance(operation, Swagger2Operation):
            validation_operation_cls = Swagger2ValidationOperation
        elif isinstance(operation, OpenAPIOperation):
            validation_operation_cls = OpenAPIValidationOperation
        else:
            raise ValueError(f"Invalid operation class: {type(operation)}")

        return validation_operation_cls(
            operation,
            validate_responses=self.validate_responses,
            strict_validation=self.strict_validation,
            validator_map=self.validator_map,
            uri_parser_class=self.uri_parser_class,
        )

    def _add_operation_internal(
        self, operation_id: str, operation: "AbstractValidationOperation"
    ):
        self.operations[operation_id] = operation


class AbstractValidationOperation:
    def __init__(
        self,
        operation: AbstractOperation,
        validate_responses: bool = False,
        strict_validation: bool = False,
        validator_map: t.Optional[dict] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
    ) -> None:
        self._operation = operation
        validate_responses = validate_responses
        strict_validation = strict_validation
        self._validator_map = dict(VALIDATOR_MAP)
        self._validator_map.update(validator_map or {})
        # TODO: Change URI parser class for middleware
        self._uri_parser_class = uri_parser_class
        self._async_uri_parser_class = {
            Swagger2URIParser: AsyncSwagger2URIParser,
            OpenAPIURIParser: AsyncOpenAPIURIParser,
        }.get(uri_parser_class, AsyncOpenAPIURIParser)
        self.validation_fn = self._get_validation_fn()

    @classmethod
    def from_operation(
        cls,
        operation,
        validate_responses=False,
        strict_validation=False,
        validator_map=None,
        uri_parser_class=None,
    ):
        raise NotImplementedError

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

    @property
    def validate_responses(self):
        """
        If True, check the response against the response schema, and return an
        error if the response does not validate.
        """
        return self._validate_responses

    def _get_validation_fn(self):
        async def function(request):
            pass

        # function = self._uri_parsing_decorator(function)

        return function

    @property
    def _uri_parsing_decorator(self):
        """
        Returns a decorator that parses request data and handles things like
        array types, and duplicate parameter definitions.
        """
        # TODO: Instantiate the class only once?
        return self._async_uri_parser_class(self.parameters, self.body_definition)

    async def __call__(self, request):
        await self.validation_fn(request)

    def __getattr__(self, name):
        """For now, we just forward any missing methods to the other operation class."""
        return getattr(self._operation, name)


class Swagger2ValidationOperation(AbstractValidationOperation):
    @classmethod
    def from_operation(
        cls,
        operation,
        validate_responses=False,
        strict_validation=False,
        validator_map=None,
        uri_parser_class=None,
    ):
        return cls(
            operation=operation,
            validate_responses=validate_responses,
            strict_validation=strict_validation,
            validator_map=validator_map,
            uri_parser_class=uri_parser_class,
        )


class OpenAPIValidationOperation(AbstractValidationOperation):
    @classmethod
    def from_operation(
        cls,
        operation,
        validate_responses=False,
        strict_validation=False,
        validator_map=None,
        uri_parser_class=None,
    ):
        return cls(
            operation=operation,
            validate_responses=validate_responses,
            strict_validation=strict_validation,
            validator_map=validator_map,
            uri_parser_class=uri_parser_class,
        )


class MissingValidationOperation(Exception):
    """Missing validation operation"""


class AbstractAsyncURIParser(AbstractURIParser):
    """URI Parser with support for async requests."""

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        async def wrapper(request: MiddlewareRequest):
            def coerce_dict(md):
                """MultiDict -> dict of lists"""
                if isinstance(md, ImmutableMultiDict):
                    # Starlette MultiDict doesn't have same interface as werkzeug one
                    return {k: md.getlist(k) for k in md}
                try:
                    return md.to_dict(flat=False)
                except AttributeError:
                    return dict(md.items())

            query = coerce_dict(request.query_params)
            path_params = coerce_dict(request.path_params)
            # FIXME
            # Read JSON first to try circumvent stream consumed error (because form doesn't story anything in self._body)
            # Potential alternative: refactor such that parsing/validation only calls the methods/properties when necessary
            try:
                json = await request.json()
            except ValueError as e:
                json = None
            # Flask splits up file uploads and text input in `files` and `form`,
            # while starlette puts them both in `form`
            form = await request.form()
            form = coerce_dict(form)
            form_parameters = {k: v for k, v in form.items() if isinstance(v, str)}
            form_files = {k: v for k, v in form.items() if isinstance(v, UploadFile)}
            for v in form.values():
                if not isinstance(v, (list, str, UploadFile)):
                    raise TypeError(f"Unexpected type in form: {type(v)} with value: {v}")

            # Construct ConnexionRequest

            request = ConnexionRequest(
                url=str(request.url),
                method=request.method,
                path_params=self.resolve_path(path_params),
                query=self.resolve_query(query),
                headers=request.headers,
                form=self.resolve_form(form_parameters),
                body=await request.body(),
                json_getter=lambda: json,
                files=form_files,
                context=request.context,
                cookies=request.cookies,
            )
            request.query = self.resolve_query(query)
            request.path_params = self.resolve_path(path_params)
            request.form = self.resolve_form(form)

            response = await function(request)
            return response

        return wrapper


class AsyncSwagger2URIParser(AbstractAsyncURIParser, Swagger2URIParser):
    """Swagger2URIParser with support for async requests."""


class AsyncOpenAPIURIParser(AbstractAsyncURIParser, OpenAPIURIParser):
    """OpenAPIURIParser with support for async requests."""
