import json
import logging
import typing as t

import jsonschema
from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.types import Scope, Send

from connexion.exceptions import BadRequestProblem, NonConformingResponseBody
from connexion.json_schema import (
    Draft4RequestValidator,
    Draft4ResponseValidator,
    format_error_with_path,
)
from connexion.utils import is_null
from connexion.validators import AbstractRequestBodyValidator

logger = logging.getLogger(__name__)


class JSONRequestBodyValidator(AbstractRequestBodyValidator):
    """Request body validator for json content types."""

    def __init__(
        self,
        *,
        schema: dict,
        required=False,
        nullable=False,
        encoding: str,
        strict_validation: bool,
        **kwargs,
    ) -> None:
        super().__init__(
            schema=schema,
            required=required,
            nullable=nullable,
            encoding=encoding,
            strict_validation=strict_validation,
        )

    @property
    def _validator(self):
        return Draft4RequestValidator(
            self._schema, format_checker=draft4_format_checker
        )

    async def _parse(
        self, stream: t.AsyncGenerator[bytes, None], scope: Scope
    ) -> t.Union[dict, str]:
        bytes_body = b"".join([message async for message in stream])
        body = bytes_body.decode(self._encoding)

        if self._nullable and is_null(body):
            return body

        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise BadRequestProblem(detail=str(e))

    def _validate(self, body: dict) -> None:
        try:
            return self._validator.validate(body)
        except ValidationError as exception:
            error_path_msg = format_error_with_path(exception=exception)
            logger.error(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise BadRequestProblem(detail=f"{exception.message}{error_path_msg}")


class DefaultsJSONRequestBodyValidator(JSONRequestBodyValidator):
    """Request body validator for json content types which fills in default values. This Validator
    intercepts the body, makes changes to it, and replays it for the next ASGI application."""

    MUTABLE_VALIDATION = True
    """This validator might mutate to the body."""

    @property
    def _validator(self):
        validator_cls = self.extend_with_set_default(Draft4RequestValidator)
        return validator_cls(self._schema, format_checker=draft4_format_checker)

    # via https://python-jsonschema.readthedocs.io/
    @staticmethod
    def extend_with_set_default(validator_class):
        validate_properties = validator_class.VALIDATORS["properties"]

        def set_defaults(validator, properties, instance, schema):
            for property, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(property, subschema["default"])

            yield from validate_properties(validator, properties, instance, schema)

        return jsonschema.validators.extend(
            validator_class, {"properties": set_defaults}
        )


class JSONResponseBodyValidator:
    """Response body validator for json content types."""

    def __init__(
        self,
        scope: Scope,
        send: Send,
        *,
        schema: dict,
        validator: t.Type[Draft4Validator] = Draft4ResponseValidator,
        nullable=False,
        encoding: str,
    ) -> None:
        self._scope = scope
        self._send = send
        self.schema = schema
        self.has_default = schema.get("default", False)
        self.nullable = nullable
        self.validator = validator(schema, format_checker=draft4_format_checker)
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
                detail=f"Response body does not conform to specification. {exception.message}{error_path_msg}"
            )

    def parse(self, body: str) -> dict:
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise NonConformingResponseBody(str(e))

    async def send(self, message: t.MutableMapping[str, t.Any]) -> None:
        self._messages.append(message)

        if message["type"] == "http.response.start" or message.get("more_body", False):
            return

        bytes_body = b"".join([message.get("body", b"") for message in self._messages])
        decoded_body = bytes_body.decode(self.encoding)

        if decoded_body and not (self.nullable and is_null(decoded_body)):
            body = self.parse(decoded_body)
            self.validate(body)

        while self._messages:
            await self._send(self._messages.pop(0))


class TextResponseBodyValidator(JSONResponseBodyValidator):
    def parse(self, body: str) -> str:  # type: ignore
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError:
            return body
