"""
Contains validator classes used by the validation middleware.
"""
import json
import logging
import typing as t

from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.types import Receive, Scope, Send

from connexion.decorators.validation import ParameterValidator
from connexion.exceptions import BadRequestProblem, NonConformingResponseBody
from connexion.json_schema import Draft4RequestValidator, Draft4ResponseValidator
from connexion.utils import is_null

logger = logging.getLogger("connexion.middleware.validators")


class JSONRequestBodyValidator:
    """Request body validator for json content types."""

    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        *,
        schema: dict,
        validator: t.Type[Draft4Validator] = None,
        nullable=False,
        encoding: str,
    ) -> None:
        self._scope = scope
        self._receive = receive
        self.schema = schema
        self.has_default = schema.get("default", False)
        self.nullable = nullable
        validator_cls = validator or Draft4RequestValidator
        self.validator = validator_cls(schema, format_checker=draft4_format_checker)
        self.encoding = encoding
        self._messages: t.List[t.MutableMapping[str, t.Any]] = []

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

    async def receive(self) -> t.Optional[t.MutableMapping[str, t.Any]]:
        more_body = True
        while more_body:
            message = await self._receive()
            self._messages.append(message)
            more_body = message.get("more_body", False)

        # TODO: make json library pluggable
        bytes_body = b"".join([message.get("body", b"") for message in self._messages])
        decoded_body = bytes_body.decode(self.encoding)

        if decoded_body and not (self.nullable and is_null(decoded_body)):
            try:
                body = json.loads(decoded_body)
            except json.decoder.JSONDecodeError as e:
                raise BadRequestProblem(str(e))

            self.validate(body)

        while self._messages:
            return self._messages.pop(0)
        return None


class JSONResponseBodyValidator:
    """Response body validator for json content types."""

    def __init__(
        self,
        scope: Scope,
        send: Send,
        *,
        schema: dict,
        validator: t.Type[Draft4Validator] = None,
        nullable=False,
        encoding: str,
    ) -> None:
        self._scope = scope
        self._send = send
        self.schema = schema
        self.has_default = schema.get("default", False)
        self.nullable = nullable
        validator_cls = validator or Draft4ResponseValidator
        self.validator = validator_cls(schema, format_checker=draft4_format_checker)
        self.encoding = encoding
        self._messages: t.List[t.MutableMapping[str, t.Any]] = []

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
            raise NonConformingResponseBody(
                message=f"{exception.message}{error_path_msg}"
            )

    @staticmethod
    def parse(body: str) -> dict:
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise BadRequestProblem(str(e))

    async def send(self, message: t.MutableMapping[str, t.Any]) -> None:
        self._messages.append(message)

        if message["type"] == "http.response.start" or message.get("more_body", False):
            return

        # TODO: make json library pluggable
        bytes_body = b"".join([message.get("body", b"") for message in self._messages])
        decoded_body = bytes_body.decode(self.encoding)

        if decoded_body and not (self.nullable and is_null(decoded_body)):
            body = self.parse(decoded_body)
            self.validate(body)

        while self._messages:
            await self._send(self._messages.pop(0))


class TextResponseBodyValidator(JSONResponseBodyValidator):
    @staticmethod
    def parse(body: str) -> str:  # type: ignore
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError:
            return body


VALIDATOR_MAP = {
    "parameter": ParameterValidator,
    "body": {"application/json": JSONRequestBodyValidator},
    "response": {
        "application/json": JSONResponseBodyValidator,
        "text/plain": TextResponseBodyValidator,
    },
}
