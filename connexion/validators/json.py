import json
import logging
import typing as t

import jsonschema
from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.types import Receive, Scope, Send

from connexion.exceptions import BadRequestProblem, NonConformingResponseBody
from connexion.json_schema import Draft4RequestValidator, Draft4ResponseValidator
from connexion.utils import is_null

logger = logging.getLogger("connexion.validators.json")


class JSONRequestBodyValidator:
    """Request body validator for json content types."""

    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        *,
        schema: dict,
        validator: t.Type[Draft4Validator] = Draft4RequestValidator,
        nullable=False,
        encoding: str,
        **kwargs,
    ) -> None:
        self._scope = scope
        self._receive = receive
        self.schema = schema
        self.has_default = schema.get("default", False)
        self.nullable = nullable
        self.validator = validator(schema, format_checker=draft4_format_checker)
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

    def parse(self, body: str) -> dict:
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise BadRequestProblem(str(e))

    async def wrapped_receive(self) -> Receive:
        more_body = True
        messages = []
        while more_body:
            message = await self._receive()
            messages.append(message)
            more_body = message.get("more_body", False)

        bytes_body = b"".join([message.get("body", b"") for message in messages])
        decoded_body = bytes_body.decode(self.encoding)

        if decoded_body and not (self.nullable and is_null(decoded_body)):
            body = self.parse(decoded_body)
            self.validate(body)

        async def receive() -> t.MutableMapping[str, t.Any]:
            while messages:
                return messages.pop(0)
            return await self._receive()

        return receive


class DefaultsJSONRequestBodyValidator(JSONRequestBodyValidator):
    """Request body validator for json content types which fills in default values. This Validator
    intercepts the body, makes changes to it, and replays it for the next ASGI application."""

    def __init__(self, *args, **kwargs):
        defaults_validator = self.extend_with_set_default(Draft4RequestValidator)
        super().__init__(*args, validator=defaults_validator, **kwargs)

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

    async def read_body(self) -> t.Tuple[str, int]:
        """Read the body from the receive channel.

        :return: A tuple (body, max_length) where max_length is the length of the largest message.
        """
        more_body = True
        max_length = 256000
        messages = []
        while more_body:
            message = await self._receive()
            max_length = max(max_length, len(message.get("body", b"")))
            messages.append(message)
            more_body = message.get("more_body", False)

        bytes_body = b"".join([message.get("body", b"") for message in messages])

        return bytes_body.decode(self.encoding), max_length

    async def wrapped_receive(self) -> Receive:
        """Receive channel to pass on to next ASGI application."""
        decoded_body, max_length = await self.read_body()

        # Validate the body if not null
        if decoded_body and not (self.nullable and is_null(decoded_body)):
            body = self.parse(decoded_body)
            del decoded_body
            self.validate(body)
            str_body = json.dumps(body)
        else:
            str_body = decoded_body

        bytes_body = str_body.encode(self.encoding)
        del str_body

        # Recreate ASGI messages from validated body so changes made by the validator are propagated
        messages = [
            {
                "type": "http.request",
                "body": bytes_body[i : i + max_length],
                "more_body": i + max_length < len(bytes_body),
            }
            for i in range(0, len(bytes_body), max_length)
        ]
        del bytes_body

        async def receive() -> t.MutableMapping[str, t.Any]:
            while messages:
                return messages.pop(0)
            return await self._receive()

        return receive


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
                message=f"{exception.message}{error_path_msg}"
            )

    def parse(self, body: str) -> dict:
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise BadRequestProblem(str(e))

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
