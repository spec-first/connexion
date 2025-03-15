"""
Validation Middleware.
"""
import logging
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion import utils
from connexion.datastructures import MediaTypeDict
from connexion.exceptions import NonConformingResponseHeaders
from connexion.middleware.abstract import RoutedAPI, RoutedMiddleware
from connexion.operations import AbstractOperation
from connexion.validators import VALIDATOR_MAP

logger = logging.getLogger("connexion.middleware.validation")


class ResponseValidationOperation:
    def __init__(
        self,
        next_app: ASGIApp,
        *,
        operation: AbstractOperation,
        validator_map: t.Optional[dict] = None,
    ) -> None:
        self.next_app = next_app
        self._operation = operation
        self._validator_map = VALIDATOR_MAP.copy()
        self._validator_map.update(validator_map or {})

    def extract_content_type(
        self, headers: t.List[t.Tuple[bytes, bytes]]
    ) -> t.Tuple[str, str]:
        """Extract the mime type and encoding from the content type headers.

        :param headers: Headers from ASGI scope

        :return: A tuple of mime type, encoding
        """
        content_type = utils.extract_content_type(headers)
        mime_type, encoding = utils.split_content_type(content_type)
        if mime_type is None:
            # Content-type header is not required. Take a best guess.
            try:
                mime_type = self._operation.produces[0]
            except IndexError:
                mime_type = "application/octet-stream"
        if encoding is None:
            encoding = "utf-8"

        return mime_type, encoding

    def validate_mime_type(self, mime_type: str) -> None:
        """Validate the mime type against the spec if it defines which mime types are produced.

        :param mime_type: mime type from content type header
        """
        if not self._operation.produces:
            return

        media_type_dict = MediaTypeDict(
            [(p.lower(), None) for p in self._operation.produces]
        )
        if mime_type.lower() not in media_type_dict:
            raise NonConformingResponseHeaders(
                detail=f"Invalid Response Content-type ({mime_type}), "
                f"expected {self._operation.produces}",
            )

    @staticmethod
    def validate_required_headers(
        headers: t.List[tuple], response_definition: dict
    ) -> None:
        required_header_keys = {
            k.lower()
            for (k, v) in response_definition.get("headers", {}).items()
            if v.get("required", False)
        }
        header_keys = set(header[0].decode("latin-1").lower() for header in headers)
        missing_keys = required_header_keys - header_keys
        if missing_keys:
            pretty_list = ", ".join(missing_keys)
            msg = (
                "Keys in response header don't match response specification. Difference: {}"
            ).format(pretty_list)
            raise NonConformingResponseHeaders(detail=msg)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        async def wrapped_send(message: t.MutableMapping[str, t.Any]) -> None:
            nonlocal send

            if message["type"] == "http.response.start":
                headers = message["headers"]

                mime_type, encoding = self.extract_content_type(headers)
                if message["status"] < 400:
                    self.validate_mime_type(mime_type)

                status = str(message["status"])
                response_definition = self._operation.response_definition(
                    status, mime_type
                )
                self.validate_required_headers(headers, response_definition)

                # Validate body
                try:
                    body_validator = self._validator_map["response"][mime_type]  # type: ignore
                except KeyError:
                    logger.info(
                        f"Skipping validation. No validator registered for content type: "
                        f"{mime_type}."
                    )
                else:
                    validator = body_validator(
                        scope,
                        schema=self._operation.response_schema(status, mime_type),
                        nullable=utils.is_nullable(
                            self._operation.response_definition(status, mime_type)
                        ),
                        encoding=encoding,
                    )
                    send = validator.wrap_send(send)

            return await send(message)

        await self.next_app(scope, receive, wrapped_send)


class ResponseValidationAPI(RoutedAPI[ResponseValidationOperation]):
    """Validation API."""

    def __init__(
        self,
        *args,
        validator_map=None,
        validate_responses=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.validator_map = validator_map
        self.validate_responses = validate_responses
        self.add_paths()

    def make_operation(
        self, operation: AbstractOperation
    ) -> ResponseValidationOperation:
        if self.validate_responses:
            return ResponseValidationOperation(
                self.next_app,
                operation=operation,
                validator_map=self.validator_map,
            )
        else:
            return self.next_app  # type: ignore


class ResponseValidationMiddleware(RoutedMiddleware[ResponseValidationAPI]):
    """Middleware for validating requests according to the API contract."""

    api_cls = ResponseValidationAPI
