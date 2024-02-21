import logging
import typing as t

from jsonschema import ValidationError, draft4_format_checker
from starlette.datastructures import Headers, UploadFile
from starlette.formparsers import FormParser, MultiPartParser
from starlette.types import Scope

from connexion.exceptions import BadRequestProblem, ExtraParameterProblem
from connexion.json_schema import Draft4RequestValidator, format_error_with_path
from connexion.uri_parsing import AbstractURIParser
from connexion.validators import AbstractRequestBodyValidator

logger = logging.getLogger("connexion.validators.form_data")


class FormDataValidator(AbstractRequestBodyValidator):
    """Request body validator for form content types."""

    def __init__(
        self,
        *,
        schema: dict,
        required=False,
        nullable=False,
        encoding: str,
        strict_validation: bool,
        uri_parser: t.Optional[AbstractURIParser] = None,
    ) -> None:
        super().__init__(
            schema=schema,
            required=required,
            nullable=nullable,
            encoding=encoding,
            strict_validation=strict_validation,
        )
        self._uri_parser = uri_parser

    @property
    def _validator(self):
        return Draft4RequestValidator(
            self._schema, format_checker=draft4_format_checker
        )

    @property
    def _form_parser_cls(self):
        return FormParser

    async def _parse(self, stream: t.AsyncGenerator[bytes, None], scope: Scope) -> dict:
        headers = Headers(scope=scope)
        form_parser = self._form_parser_cls(headers, stream)
        data = await form_parser.parse()

        if self._uri_parser is not None:
            # Don't parse file_data
            form_data = {}
            file_data: t.Dict[str, t.Union[str, t.List[str]]] = {}
            for key in data.keys():
                # Extract files
                param_schema = self._schema.get("properties", {}).get(key, {})
                value = data.getlist(key)

                def is_file(schema):
                    return schema.get("type") == "string" and schema.get("format") in [
                        "binary",
                        "base64",
                    ]

                # Single file upload
                if is_file(param_schema):
                    # Unpack if single file received
                    if len(value) == 1:
                        file_data[key] = ""
                    # If multiple files received, replace with array so validation will fail
                    else:
                        file_data[key] = [""] * len(value)
                # Multiple file upload, replace files with array of strings
                elif is_file(param_schema.get("items", {})):
                    file_data[key] = [""] * len(value)
                # UploadFile received for non-file upload. Replace and let validation handle.
                elif isinstance(value[0], UploadFile):
                    file_data[key] = [""] * len(value)
                # No files, add multi-value to form data and let uri parser handle multi-value
                else:
                    form_data[key] = value

            # Resolve form data, not file data
            data = self._uri_parser.resolve_form(form_data)
            # Add the files again
            data.update(file_data)
        else:
            data = {k: data.getlist(k) for k in data}

        return data

    def _validate(self, body: t.Any) -> t.Optional[dict]:  # type: ignore[return]
        if not isinstance(body, dict):
            raise BadRequestProblem("Parsed body must be a mapping")
        if self._strict_validation:
            self._validate_params_strictly(body)
        try:
            self._validator.validate(body)
        except ValidationError as exception:
            error_path_msg = format_error_with_path(exception=exception)
            logger.error(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise BadRequestProblem(detail=f"{exception.message}{error_path_msg}")

    def _validate_params_strictly(self, data: dict) -> None:
        form_params = data.keys()
        spec_params = self._schema.get("properties", {}).keys()
        errors = set(form_params).difference(set(spec_params))
        if errors:
            raise ExtraParameterProblem(param_type="formData", extra_params=errors)


class MultiPartFormDataValidator(FormDataValidator):
    @property
    def _form_parser_cls(self):
        return MultiPartParser
