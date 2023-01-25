import logging
import typing as t

from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.formparsers import FormParser, MultiPartParser
from starlette.types import Receive, Scope

from connexion.exceptions import BadRequestProblem, ExtraParameterProblem
from connexion.json_schema import Draft4RequestValidator
from connexion.uri_parsing import AbstractURIParser
from connexion.utils import is_null

logger = logging.getLogger("connexion.validators.form_data")


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

    def _parse(self, data: FormData) -> dict:
        if self.uri_parser is not None:
            # Don't parse file_data
            form_data = {}
            file_data = {}
            for k, v in data.items():
                if isinstance(v, str):
                    form_data[k] = data.getlist(k)
                elif isinstance(v, UploadFile):
                    # Replace files with empty strings for validation
                    file_data[k] = ""

            data = self.uri_parser.resolve_form(form_data)
            # Add the files again
            data.update(file_data)
        else:
            data = {k: data.getlist(k) for k in data}

        return data

    def _validate_strictly(self, data: FormData) -> None:
        form_params = data.keys()
        spec_params = self.schema.get("properties", {}).keys()
        errors = set(form_params).difference(set(spec_params))
        if errors:
            raise ExtraParameterProblem(errors, [])

    def validate(self, data: FormData) -> None:
        if self.strict_validation:
            self._validate_strictly(data)

        data = self._parse(data)
        self._validate(data)

    async def wrapped_receive(self) -> Receive:
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

        if form and not (self.nullable and is_null(form)):
            self.validate(form)

        async def receive() -> t.MutableMapping[str, t.Any]:
            while self._messages:
                return self._messages.pop(0)
            return await self._receive()

        return receive


class MultiPartFormDataValidator(FormDataValidator):
    @property
    def form_parser_cls(self):
        return MultiPartParser
