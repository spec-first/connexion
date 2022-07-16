"""
Validation Middleware.
"""
import logging
import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.abstract import AbstractSpecAPI
from connexion.decorators.uri_parsing import AbstractURIParser
from connexion.exceptions import MissingMiddleware, ResolverError
from connexion.http_facts import METHODS
from connexion.lifecycle import MiddlewareRequest
from connexion.middleware import AppMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from connexion.operations.abstract import AbstractOperation
from connexion.operations.openapi import OpenAPIOperation
from connexion.operations.swagger2 import Swagger2Operation

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
                else:
                    raise MissingValidationOperation(
                        "Encountered unknown operation_id."
                    ) from e
            else:
                # TODO: Add validation logic
                request = MiddlewareRequest(scope)
                await operation(request)

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
        self._uri_parser_class = uri_parser_class
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

        return function

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
