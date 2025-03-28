import json
import logging
import typing as t

import jsonschema
from jsonschema import Draft4Validator, Draft7Validator, Draft202012Validator, ValidationError
from starlette.types import Scope

from connexion.exceptions import BadRequestProblem, NonConformingResponseBody
from connexion.json_schema import (
    Draft4RequestValidator,
    Draft4ResponseValidator,
    Draft7RequestValidator,
    Draft7ResponseValidator,
    Draft2020RequestValidator,
    Draft2020ResponseValidator,
    format_error_with_path,
)
from connexion.validators import (
    AbstractRequestBodyValidator,
    AbstractResponseBodyValidator,
)

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
        schema_dialect=None,
        **kwargs,
    ) -> None:
        super().__init__(
            schema=schema,
            required=required,
            nullable=nullable,
            encoding=encoding,
            strict_validation=strict_validation,
        )
        self._schema_dialect = schema_dialect

    @property
    def _validator(self):
        # Use Draft2020 validator for OpenAPI 3.1
        if self._schema_dialect and 'draft/2020-12' in self._schema_dialect:
            return Draft2020RequestValidator(
                self._schema, format_checker=Draft202012Validator.FORMAT_CHECKER
            )
        # Default to Draft4 for backward compatibility
        return Draft4RequestValidator(
            self._schema, format_checker=Draft4Validator.FORMAT_CHECKER
        )

    async def _parse(
        self, stream: t.AsyncGenerator[bytes, None], scope: Scope
    ) -> t.Any:
        bytes_body = b"".join([message async for message in stream])
        body = bytes_body.decode(self._encoding)

        if not body:
            return None

        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise BadRequestProblem(detail=str(e))

    def _validate(self, body: t.Any) -> t.Optional[dict]:
        if not self._nullable and body is None:
            raise BadRequestProblem("Request body must not be empty")
        try:
            return self._validator.validate(body)
        except ValidationError as exception:
            error_path_msg = format_error_with_path(exception=exception)
            logger.info(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise BadRequestProblem(detail=f"{exception.message}{error_path_msg}")


class DefaultsJSONRequestBodyValidator(JSONRequestBodyValidator):
    """Request body validator for json content types which fills in default values. This Validator
    intercepts the body, makes changes to it, and replays it for the next ASGI application.
    """

    MUTABLE_VALIDATION = True
    """This validator might mutate to the body."""

    @property
    def _validator(self):
        # Use Draft2020 validator for OpenAPI 3.1
        if self._schema_dialect and 'draft/2020-12' in self._schema_dialect:
            validator_cls = self.extend_with_set_default(Draft2020RequestValidator)
            return validator_cls(
                self._schema, format_checker=Draft202012Validator.FORMAT_CHECKER
            )
        # Default to Draft4 for backward compatibility
        validator_cls = self.extend_with_set_default(Draft4RequestValidator)
        return validator_cls(
            self._schema, format_checker=Draft4Validator.FORMAT_CHECKER
        )

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


class JSONResponseBodyValidator(AbstractResponseBodyValidator):
    """Response body validator for json content types."""

    def __init__(
        self,
        scope: t.Optional[Scope] = None,
        *,
        schema: dict,
        encoding: str,
        nullable: bool = False,
        strict_validation: bool = False,
        schema_dialect=None,
        **kwargs,
    ) -> None:
        super().__init__(
            scope=scope,
            schema=schema,
            encoding=encoding,
            nullable=nullable,
            strict_validation=strict_validation,
        )
        self._schema_dialect = schema_dialect

    @property
    def validator(self):
        # Use Draft2020 validator for OpenAPI 3.1
        if self._schema_dialect and 'draft/2020-12' in self._schema_dialect:
            return Draft2020ResponseValidator(
                self._schema, format_checker=Draft202012Validator.FORMAT_CHECKER
            )
        # Default to Draft4 for backward compatibility 
        return Draft4ResponseValidator(
            self._schema, format_checker=Draft4Validator.FORMAT_CHECKER
        )

    def _parse(self, stream: t.Generator[bytes, None, None]) -> t.Any:
        body = b"".join(stream).decode(self._encoding)

        if not body:
            return None

        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError as e:
            raise NonConformingResponseBody(str(e))

    def _validate(self, body: dict):
        try:
            self.validator.validate(body)
        except ValidationError as exception:
            error_path_msg = format_error_with_path(exception=exception)
            logger.warning(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise NonConformingResponseBody(
                detail=f"Response body does not conform to specification. {exception.message}{error_path_msg}"
            )


class TextResponseBodyValidator(JSONResponseBodyValidator):
    def __init__(
        self,
        scope: t.Optional[Scope] = None,
        *,
        schema: dict,
        encoding: str,
        nullable: bool = False,
        strict_validation: bool = False,
        schema_dialect=None,
        **kwargs,
    ) -> None:
        super().__init__(
            scope=scope,
            schema=schema,
            encoding=encoding,
            nullable=nullable,
            strict_validation=strict_validation,
            schema_dialect=schema_dialect,
            **kwargs
        )
        
    def _parse(self, stream: t.Generator[bytes, None, None]) -> str:  # type: ignore
        body = b"".join(stream).decode(self._encoding)

        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError:
            return body
