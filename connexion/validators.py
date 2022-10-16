"""
Contains validator classes used by the validation middleware.
"""
import json
import logging
import typing as t

from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.formparsers import FormParser, MultiPartParser
from starlette.types import Receive, Scope, Send

from connexion.datastructures import MediaTypeDict
from connexion.decorators.uri_parsing import AbstractURIParser
from connexion.decorators.validation import (
    ParameterValidator,
    TypeValidationError,
    coerce_type,
)
from connexion.exceptions import (
    BadRequestProblem,
    ExtraParameterProblem,
    NonConformingResponseBody,
)
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

    @staticmethod
    def parse(body: str) -> dict:
        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise BadRequestProblem(str(e))

    async def wrapped_receive(self) -> Receive:
        more_body = True
        while more_body:
            message = await self._receive()
            self._messages.append(message)
            more_body = message.get("more_body", False)

        bytes_body = b"".join([message.get("body", b"") for message in self._messages])
        decoded_body = bytes_body.decode(self.encoding)

        if decoded_body and not (self.nullable and is_null(decoded_body)):
            body = self.parse(decoded_body)
            self.validate(body)

        async def receive() -> t.MutableMapping[str, t.Any]:
            while self._messages:
                return self._messages.pop(0)
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


class FormDataValidator:
    """Request body validator for form content types."""

    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        *,
        schema: dict,
        validator: t.Type[Draft4Validator] = None,
        uri_parser: t.Optional[AbstractURIParser] = None,
        nullable=False,
        encoding: str,
        strict_validation: bool,
    ) -> None:
        self._scope = scope
        self._receive = receive
        self.schema = schema
        self.has_default = schema.get("default", False)
        self.nullable = nullable
        validator_cls = validator or Draft4RequestValidator
        self.validator = validator_cls(schema, format_checker=draft4_format_checker)
        self.uri_parser = uri_parser
        self.encoding = encoding
        self._messages: t.List[t.MutableMapping[str, t.Any]] = []
        self.headers = Headers(scope=scope)
        self.strict_validation = strict_validation
        self.check_empty()

    @property
    def form_parser_cls(self):
        return FormParser

    def check_empty(self):
        """`receive` is never called if body is empty, so we need to check this case at
        initialization."""
        if not int(self.headers.get("content-length", 0)) and self.schema.get(
            "required", []
        ):
            self._validate({})

    @classmethod
    def _error_path_message(cls, exception):
        error_path = ".".join(str(item) for item in exception.path)
        error_path_msg = f" - '{error_path}'" if error_path else ""
        return error_path_msg

    def _validate(self, data: dict) -> None:
        try:
            self.validator.validate(data)
        except ValidationError as exception:
            error_path_msg = self._error_path_message(exception=exception)
            logger.error(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise BadRequestProblem(detail=f"{exception.message}{error_path_msg}")

    def validate(self, data: FormData) -> None:
        if self.strict_validation:
            form_params = data.keys()
            spec_params = self.schema.get("properties", {}).keys()
            errors = set(form_params).difference(set(spec_params))
            if errors:
                raise ExtraParameterProblem(errors, [])

        if data:
            props = self.schema.get("properties", {})
            errs = []
            if self.uri_parser is not None:
                # TODO: Make more efficient
                # Flask splits up file uploads and text input in `files` and `form`,
                # while starlette puts them both in `form`
                form_keys = {k for k, v in data.items() if isinstance(v, str)}
                file_data = {k: v for k, v in data.items() if isinstance(v, UploadFile)}
                data = {k: data.getlist(k) for k in form_keys}
                data = self.uri_parser.resolve_form(data)
                # Add the files again
                data.update(file_data)
            else:
                data = dict(data)  # TODO: preserve multi-item?
            for k, param_defn in props.items():
                if k in data:
                    if param_defn.get("format", "") == "binary":
                        # Replace files with empty strings for validation
                        data[k] = ""
                        continue

                    try:
                        data[k] = coerce_type(param_defn, data[k], "requestBody", k)
                    except TypeValidationError as e:
                        logger.exception(e)
                        errs += [str(e)]
            if errs:
                raise BadRequestProblem(detail=errs)

        self._validate(data)

    async def wrapped_receive(self) -> Receive:

        if not self.schema:
            # swagger 2
            return self._receive

        async def stream() -> t.AsyncGenerator[bytes, None]:
            more_body = True
            while more_body:
                message = await self._receive()
                self._messages.append(message)
                more_body = message.get("more_body", False)
                yield message.get("body", b"")
            yield b""

        form_parser = self.form_parser_cls(self.headers, stream())
        form = await form_parser.parse()

        if not (self.nullable and is_null(form)):
            self.validate(form or {})

        async def receive() -> t.MutableMapping[str, t.Any]:
            while self._messages:
                return self._messages.pop(0)
            return await self._receive()

        return receive


class MultiPartFormDataValidator(FormDataValidator):
    @property
    def form_parser_cls(self):
        return MultiPartParser


VALIDATOR_MAP = {
    "parameter": ParameterValidator,
    "body": MediaTypeDict(
        {
            "*/*json": JSONRequestBodyValidator,
            "application/x-www-form-urlencoded": FormDataValidator,
            "multipart/form-data": MultiPartFormDataValidator,
        }
    ),
    "response": MediaTypeDict(
        {
            "*/*json": JSONResponseBodyValidator,
            "text/plain": TextResponseBodyValidator,
        }
    ),
}
