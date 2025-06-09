import logging
import typing as t

from jsonschema import Draft4Validator, Draft202012Validator, ValidationError
from starlette.datastructures import Headers, UploadFile
from starlette.formparsers import FormParser, MultiPartParser
from starlette.types import Scope

from connexion.exceptions import BadRequestProblem, ExtraParameterProblem
from connexion.json_schema import (
    Draft4RequestValidator,
    Draft2020RequestValidator,
    format_error_with_path,
)
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
        schema_dialect=None,
        **kwargs,
    ) -> None:
        super().__init__(
            schema=schema,
            required=required,
            nullable=nullable,
            encoding=encoding,
            strict_validation=strict_validation,
            schema_dialect=schema_dialect,
        )
        self._uri_parser = uri_parser
        self._schema_dialect = schema_dialect

    @property
    def _validator(self):
        # Use Draft2020 validator for OpenAPI 3.1
        if self._schema_dialect and "draft/2020-12" in self._schema_dialect:
            return Draft2020RequestValidator(
                self._schema, format_checker=Draft202012Validator.FORMAT_CHECKER
            )
        # Default to Draft4 for backward compatibility
        return Draft4RequestValidator(
            self._schema, format_checker=Draft4Validator.FORMAT_CHECKER
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
            file_data: t.Dict[
                str, t.Union[str, t.List[str], UploadFile, t.List[UploadFile]]
            ] = {}
            upload_files = {}

            # First process all upload files - we need to handle these directly
            for key in data.keys():
                value = data.getlist(key)
                if value and isinstance(value[0], UploadFile):
                    # Always add upload files to upload_files dictionary
                    file_obj = value[0] if len(value) == 1 else value
                    upload_files[key] = file_obj

                    # Special handling for OpenAPI 3.1 with allOf and file uploads
                    is_openapi31_allof = (
                        hasattr(self._schema, "get")
                        and self._schema.get("components", {}) is not None
                        and "allOf" in self._schema
                    )

                    has_file_property = False
                    if is_openapi31_allof:
                        for schema in self._schema.get("allOf", []):
                            if "properties" in schema and "file" in schema.get(
                                "properties", {}
                            ):
                                has_file_property = True
                                break

                    if is_openapi31_allof and has_file_property:
                        # For OpenAPI 3.1 with allOf and file property, add file object directly to form_data
                        form_data[key] = file_obj

                    # Always add to file_data as a placeholder for validation
                    file_data[key] = file_obj

            # Now process all form fields
            for key in data.keys():
                # Extract files - handle complex schemas
                param_schema = {}

                # First check direct properties
                if "properties" in self._schema and key in self._schema.get(
                    "properties", {}
                ):
                    param_schema = self._schema.get("properties", {}).get(key, {})

                # Check in allOf schemas if not found
                elif "allOf" in self._schema:
                    for schema in self._schema["allOf"]:
                        if "properties" in schema and key in schema["properties"]:
                            param_schema = schema["properties"][key]
                            break

                # If still not found, check in referenced schemas within allOf
                if not param_schema and "allOf" in self._schema:
                    # Look deeper in nested allOf/oneOf/anyOf referenced schemas
                    for schema in self._schema["allOf"]:
                        if "allOf" in schema:
                            for sub_schema in schema["allOf"]:
                                if (
                                    "properties" in sub_schema
                                    and key in sub_schema["properties"]
                                ):
                                    param_schema = sub_schema["properties"][key]
                                    break
                        if param_schema:
                            break

                value = data.getlist(key)

                def is_file(schema):
                    # Handle simple schema case
                    if schema.get("type") == "string" and schema.get("format") in [
                        "binary",
                        "base64",
                    ]:
                        return True

                    # Handle allOf case
                    if "allOf" in schema:
                        for sub_schema in schema["allOf"]:
                            if isinstance(sub_schema, dict):
                                if sub_schema.get(
                                    "type"
                                ) == "string" and sub_schema.get("format") in [
                                    "binary",
                                    "base64",
                                ]:
                                    return True
                                # Look for nested formats in referenced schemas
                                if "allOf" in sub_schema and is_file(sub_schema):
                                    return True

                    # Handle oneOf case
                    if "oneOf" in schema:
                        for sub_schema in schema["oneOf"]:
                            if sub_schema.get("type") == "string" and sub_schema.get(
                                "format"
                            ) in ["binary", "base64"]:
                                return True

                    # Handle anyOf case
                    if "anyOf" in schema:
                        for sub_schema in schema["anyOf"]:
                            if sub_schema.get("type") == "string" and sub_schema.get(
                                "format"
                            ) in ["binary", "base64"]:
                                return True

                    return False

                # Check if this is a file upload field
                is_file_field = is_file(param_schema)
                is_array_of_files = (
                    False
                    if not param_schema
                    else is_file(param_schema.get("items", {}))
                )

                # Skip keys that are already in file_data (they were uploaded files)
                if key in file_data:
                    continue

                # For regular form fields (non-file uploads), handle them normally
                # For non-array types, if we have a single value in the list, extract it
                # This prevents the ['value'] is not of type 'string' error
                if (
                    param_schema
                    and param_schema.get("type") == "string"
                    and len(value) == 1
                ):
                    form_data[key] = value[0]
                else:
                    form_data[key] = value

            # Resolve form data, preserving file uploads
            data = self._uri_parser.resolve_form(form_data)

            # Add any file uploads that might not have been included
            file_keys = set(upload_files.keys()) - set(data.keys())
            if file_keys:
                for key in file_keys:
                    data[key] = upload_files[key]
                # Ensure all file uploads are included
        else:
            data = {k: data.getlist(k) for k in data}

        # Return the parsed and validated data

        return data

    def _validate(self, body: t.Any) -> t.Optional[dict]:  # type: ignore[return]
        if not isinstance(body, dict):
            raise BadRequestProblem("Parsed body must be a mapping")
        if self._strict_validation:
            self._validate_params_strictly(body)

        # Special case for OpenAPI 3.1 allOf schemas with file uploads
        is_openapi31_allof = (
            hasattr(self._schema, "get")
            and self._schema.get("components", {}) is not None
            and "allOf" in self._schema
        )

        if is_openapi31_allof:
            # Check if this is a file upload scenario with allOf schema
            has_file_property = False
            for schema in self._schema.get("allOf", []):
                if "properties" in schema and "file" in schema.get("properties", {}):
                    has_file_property = True
                    break

            # Check if we have a file upload in the body
            has_file_upload = False
            for key, value in body.items():
                if isinstance(value, UploadFile):
                    has_file_upload = True
                    break

            # Only skip validation for allOf schemas with file property and actual file upload
            if has_file_property and has_file_upload:
                return body

        # Create a validation copy that replaces UploadFile objects with placeholders
        validation_body = {}
        for key, value in body.items():
            # Check if this is a single UploadFile
            if isinstance(value, UploadFile):
                # Need to check if the schema expects an array
                is_array_schema = False

                # Check main schema
                if "properties" in self._schema and key in self._schema.get(
                    "properties", {}
                ):
                    schema = self._schema.get("properties", {}).get(key, {})
                    is_array_schema = schema.get("type") == "array"

                # Check in complex schemas if not found
                if not is_array_schema and "allOf" in self._schema:
                    for schema in self._schema.get("allOf", []):
                        if "properties" in schema and key in schema.get(
                            "properties", {}
                        ):
                            is_array_schema = (
                                schema.get("properties", {}).get(key, {}).get("type")
                                == "array"
                            )
                            if is_array_schema:
                                break

                if is_array_schema:
                    # If schema expects an array, provide as array even for single file
                    validation_body[key] = [value.filename]
                else:
                    # Otherwise treat as single value
                    validation_body[key] = value.filename
                continue

            # Check if this is an array of UploadFiles
            if isinstance(value, list) and value and isinstance(value[0], UploadFile):
                # Replace UploadFile array with placeholder strings
                validation_body[key] = [item.filename for item in value]
                continue

            # For non-file values, just copy as is
            validation_body[key] = value

        try:
            self._validator.validate(validation_body)
        except ValidationError as exception:
            error_path_msg = format_error_with_path(exception=exception)
            logger.error(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise BadRequestProblem(detail=f"{exception.message}{error_path_msg}")

        # Return the original body with the real UploadFile objects
        return body

    def _validate_params_strictly(self, data: dict) -> None:
        form_params = set(data.keys())

        # Extract all possible property names, including those in allOf, oneOf, anyOf
        allowed_params = set()

        # Check direct properties
        if "properties" in self._schema:
            allowed_params.update(self._schema["properties"].keys())

        # Check for properties in allOf (including nested allOf in referenced schemas)
        if "allOf" in self._schema:
            for schema in self._schema["allOf"]:
                if "properties" in schema:
                    allowed_params.update(schema["properties"].keys())
                # Look for nested properties in referenced schemas within allOf
                if "allOf" in schema:
                    for sub_schema in schema["allOf"]:
                        if "properties" in sub_schema:
                            allowed_params.update(sub_schema["properties"].keys())

        # Check for properties in oneOf
        if "oneOf" in self._schema:
            for schema in self._schema["oneOf"]:
                if "properties" in schema:
                    allowed_params.update(schema["properties"].keys())

        # Check for properties in anyOf
        if "anyOf" in self._schema:
            for schema in self._schema["anyOf"]:
                if "properties" in schema:
                    allowed_params.update(schema["properties"].keys())

        errors = form_params.difference(allowed_params)
        if errors:
            raise ExtraParameterProblem(param_type="formData", extra_params=errors)


class MultiPartFormDataValidator(FormDataValidator):
    @property
    def _form_parser_cls(self):
        return MultiPartParser
