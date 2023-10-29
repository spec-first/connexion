import json
import logging
import typing as t

import jsonschema
from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from starlette.types import Scope

from connexion.exceptions import BadRequestProblem, NonConformingResponseBody
from connexion.json_schema import (
    Draft4RequestValidator,
    Draft4ResponseValidator,
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


class JSONResponseBodyValidator(AbstractResponseBodyValidator):
    """Response body validator for json content types."""

    @property
    def validator(self) -> Draft4Validator:
        return Draft4ResponseValidator(
            self._schema, format_checker=draft4_format_checker
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
            logger.error(
                f"Validation error: {exception.message}{error_path_msg}",
                extra={"validator": "body"},
            )
            raise NonConformingResponseBody(
                detail=f"Response body does not conform to specification. {exception.message}{error_path_msg}"
            )


class TextResponseBodyValidator(JSONResponseBodyValidator):
    def _parse(self, stream: t.Generator[bytes, None, None]) -> str:  # type: ignore
        body = b"".join(stream).decode(self._encoding)

        try:
            return json.loads(body)
        except json.decoder.JSONDecodeError:
            return body
