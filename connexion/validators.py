"""
Contains validator classes used by the validation middleware.
"""
import json
import logging
import typing as t

from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import BadRequestProblem
from connexion.json_schema import Draft4RequestValidator
from connexion.utils import is_null

logger = logging.getLogger("connexion.middleware.validators")


class JSONBodyValidator:
    """Request body validator for json content types."""

    def __init__(
        self,
        next_app: ASGIApp,
        *,
        schema: dict,
        validator: t.Type[Draft4Validator] = None,
        nullable=False,
        encoding: str,
    ) -> None:
        self.next_app = next_app
        self.schema = schema
        self.has_default = schema.get("default", False)
        self.nullable = nullable
        self.validator_cls = validator or Draft4RequestValidator
        self.validator = self.validator_cls(
            schema, format_checker=draft4_format_checker
        )
        self.encoding = encoding

    @classmethod
    def _error_path_message(cls, exception):
        error_path = ".".join(str(item) for item in exception.path)
        error_path_msg = f" - '{error_path}'" if error_path else ""
        return error_path_msg

    def validate(self, body: dict):

        try:
            self.validator.validate(body)
        except ValidationError as exception:
            error_path_msg = self._error_path_message(exception=exception)
            logger.error(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise BadRequestProblem(detail=f"{exception.message}{error_path_msg}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Based on https://github.com/encode/starlette/pull/1519#issuecomment-1060633787
        # Ingest all body messages from the ASGI `receive` callable.
        messages = []
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            more_body = message.get("more_body", False)

        # TODO: make json library pluggable
        bytes_body = b"".join([message.get("body", b"") for message in messages])
        decoded_body = bytes_body.decode(self.encoding)

        if decoded_body and not (self.nullable and is_null(decoded_body)):
            try:
                body = json.loads(decoded_body)
            except json.decoder.JSONDecodeError as e:
                raise BadRequestProblem(str(e))

            self.validate(body)

        async def wrapped_receive():
            # First up we want to return any messages we've stashed.
            if messages:
                return messages.pop(0)
            # Once that's done we can just await any other messages.
            return await receive()

        await self.next_app(scope, wrapped_receive, send)
