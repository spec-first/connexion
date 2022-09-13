"""
Validation Middleware.
"""
import logging
import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.abstract import AbstractSpecAPI
from connexion.decorators.uri_parsing import AbstractURIParser
from connexion.exceptions import MissingMiddleware, UnsupportedMediaTypeProblem
from connexion.http_facts import METHODS
from connexion.middleware import AppMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from connexion.operations import AbstractOperation
from connexion.resolver import ResolverError
from connexion.utils import is_nullable
from connexion.validators import JSONBodyValidator

from ..decorators.response import ResponseValidator
from ..decorators.validation import ParameterValidator

logger = logging.getLogger("connexion.middleware.validation")

VALIDATOR_MAP = {
    "parameter": ParameterValidator,
    "body": {"application/json": JSONBodyValidator},
    "response": ResponseValidator,
}


class ValidationMiddleware(AppMiddleware):
    """Middleware for validating requests according to the API contract."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, ValidationAPI] = {}

    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        api = ValidationAPI(specification, next_app=self.app, **kwargs)
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
                return await operation(scope, receive, send)

        await self.app(scope, receive, send)


class ValidationAPI(AbstractSpecAPI):
    """Validation API."""

    def __init__(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        *args,
        next_app: ASGIApp,
        validate_responses=False,
        strict_validation=False,
        validator_map=None,
        uri_parser_class=None,
        **kwargs,
    ):
        super().__init__(specification, *args, **kwargs)
        self.next_app = next_app

        self.validator_map = validator_map

        logger.debug("Validate Responses: %s", str(validate_responses))
        self.validate_responses = validate_responses

        logger.debug("Strict Request Validation: %s", str(strict_validation))
        self.strict_validation = strict_validation

        self.uri_parser_class = uri_parser_class

        self.operations: t.Dict[str, ValidationOperation] = {}
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
        return ValidationOperation(
            operation,
            self.next_app,
            validate_responses=self.validate_responses,
            strict_validation=self.strict_validation,
            validator_map=self.validator_map,
            uri_parser_class=self.uri_parser_class,
        )

    def _add_operation_internal(
        self, operation_id: str, operation: "ValidationOperation"
    ):
        self.operations[operation_id] = operation


class ValidationOperation:
    def __init__(
        self,
        operation: AbstractOperation,
        next_app: ASGIApp,
        validate_responses: bool = False,
        strict_validation: bool = False,
        validator_map: t.Optional[dict] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
    ) -> None:
        self._operation = operation
        self.next_app = next_app
        self.validate_responses = validate_responses
        self.strict_validation = strict_validation
        self._validator_map = VALIDATOR_MAP
        self._validator_map.update(validator_map or {})
        self.uri_parser_class = uri_parser_class

    def extract_content_type(self, headers: dict) -> t.Tuple[str, str]:
        """Extract the mime type and encoding from the content type headers.

        :param headers: Header dict from ASGI scope

        :return: A tuple of mime type, encoding
        """
        encoding = "utf-8"
        for key, value in headers:
            # Headers can always be decoded using latin-1:
            # https://stackoverflow.com/a/27357138/4098821
            key = key.decode("latin-1")
            if key.lower() == "content-type":
                content_type = value.decode("latin-1")
                if ";" in content_type:
                    mime_type, parameters = content_type.split(";", maxsplit=1)

                    prefix = "charset="
                    for parameter in parameters.split(";"):
                        if parameter.startswith(prefix):
                            encoding = parameter[len(prefix) :]
                else:
                    mime_type = content_type
                break
        else:
            # Content-type header is not required. Take a best guess.
            mime_type = self._operation.consumes[0]

        return mime_type, encoding

    def validate_mime_type(self, mime_type: str) -> None:
        """Validate the mime type against the spec.

        :param mime_type: mime type from content type header
        """
        if mime_type.lower() not in [c.lower() for c in self._operation.consumes]:
            raise UnsupportedMediaTypeProblem(
                detail=f"Invalid Content-type ({mime_type}), "
                f"expected {self._operation.consumes}"
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        headers = scope["headers"]
        mime_type, encoding = self.extract_content_type(headers)
        self.validate_mime_type(mime_type)

        # TODO: Validate parameters

        # Validate body
        try:
            body_validator = self._validator_map["body"][mime_type]  # type: ignore
        except KeyError:
            logging.info(
                f"Skipping validation. No validator registered for content type: "
                f"{mime_type}."
            )
        else:
            validator = body_validator(
                self.next_app,
                schema=self._operation.body_schema,
                nullable=is_nullable(self._operation.body_definition),
                encoding=encoding,
            )
            return await validator(scope, receive, send)

        await self.next_app(scope, receive, send)


class MissingValidationOperation(Exception):
    """Missing validation operation"""
