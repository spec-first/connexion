"""
Validation Middleware.
"""
import logging
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion import utils
from connexion.decorators.uri_parsing import AbstractURIParser
from connexion.exceptions import UnsupportedMediaTypeProblem
from connexion.middleware.abstract import RoutedAPI, RoutedMiddleware
from connexion.operations import AbstractOperation
from connexion.validators import VALIDATOR_MAP

logger = logging.getLogger("connexion.middleware.validation")


class RequestValidationOperation:
    def __init__(
        self,
        next_app: ASGIApp,
        *,
        operation: AbstractOperation,
        strict_validation: bool = False,
        validator_map: t.Optional[dict] = None,
        uri_parser_class: t.Optional[AbstractURIParser] = None,
    ) -> None:
        self.next_app = next_app
        self._operation = operation
        self.strict_validation = strict_validation
        self._validator_map = VALIDATOR_MAP.copy()
        self._validator_map.update(validator_map or {})
        self.uri_parser_class = uri_parser_class

    def extract_content_type(
        self, headers: t.List[t.Tuple[bytes, bytes]]
    ) -> t.Tuple[str, str]:
        """Extract the mime type and encoding from the content type headers.

        :param headers: Headers from ASGI scope

        :return: A tuple of mime type, encoding
        """
        mime_type, encoding = utils.extract_content_type(headers)
        if mime_type is None:
            # Content-type header is not required. Take a best guess.
            try:
                mime_type = self._operation.consumes[0]
            except IndexError:
                mime_type = "application/octet-stream"
        if encoding is None:
            encoding = "utf-8"

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
        receive_fn = receive

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
                scope,
                receive,
                schema=self._operation.body_schema,
                nullable=utils.is_nullable(self._operation.body_definition),
                encoding=encoding,
                strict_validation=self.strict_validation,
                uri_parser=self._operation._uri_parsing_decorator,
            )
            receive_fn = await validator.wrapped_receive()

        await self.next_app(scope, receive_fn, send)


class RequestValidationAPI(RoutedAPI[RequestValidationOperation]):
    """Validation API."""

    operation_cls = RequestValidationOperation

    def __init__(
        self,
        *args,
        strict_validation=False,
        validator_map=None,
        uri_parser_class=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.validator_map = validator_map

        logger.debug("Strict Request Validation: %s", str(strict_validation))
        self.strict_validation = strict_validation

        self.uri_parser_class = uri_parser_class

        self.add_paths()

    def make_operation(
        self, operation: AbstractOperation
    ) -> RequestValidationOperation:
        return RequestValidationOperation(
            self.next_app,
            operation=operation,
            strict_validation=self.strict_validation,
            validator_map=self.validator_map,
            uri_parser_class=self.uri_parser_class,
        )


class RequestValidationMiddleware(RoutedMiddleware[RequestValidationAPI]):
    """Middleware for validating requests according to the API contract."""

    api_cls = RequestValidationAPI


class MissingValidationOperation(Exception):
    """Missing validation operation"""
