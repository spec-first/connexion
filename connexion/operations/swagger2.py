"""
This module defines a Swagger2Operation class, a Connexion operation specific for Swagger 2 specs.
"""

import logging
import typing as t
from copy import deepcopy

from connexion.operations.abstract import AbstractOperation

from ..decorators.uri_parsing import Swagger2URIParser
from ..exceptions import InvalidSpecification
from ..http_facts import FORM_CONTENT_TYPES
from ..utils import deep_get, is_null, is_nullable, make_type

logger = logging.getLogger("connexion.operations.swagger2")


COLLECTION_FORMAT_MAPPING = {
    "multi": {"style": "form", "explode": True},
    "csv": {"style": "form", "explode": False},
    "ssv": {"style": "spaceDelimited", "explode": False},
    "pipes": {"style": "pipeDelimited", "explode": False},
}


class Swagger2Operation(AbstractOperation):

    """
    Exposes a Swagger 2.0 operation under the AbstractOperation interface.
    The primary purpose of this class is to provide the `function()` method
    to the API. A Swagger2Operation is plugged into the API with the provided
    (path, method) pair. It resolves the handler function for this operation
    with the provided resolver, and wraps the handler function with multiple
    decorators that provide security, validation, serialization,
    and deserialization.
    """

    def __init__(
        self,
        api,
        method,
        path,
        operation,
        resolver,
        app_produces,
        app_consumes,
        path_parameters=None,
        app_security=None,
        security_schemes=None,
        definitions=None,
        validate_responses=False,
        strict_validation=False,
        randomize_endpoint=None,
        validator_map=None,
        pythonic_params=False,
        uri_parser_class=None,
    ):
        """
        :param api: api that this operation is attached to
        :type api: apis.AbstractAPI
        :param method: HTTP method
        :type method: str
        :param path: relative path to this operation
        :type path: str
        :param operation: swagger operation object
        :type operation: dict
        :param resolver: Callable that maps operationID to a function
        :type resolver: resolver.Resolver
        :param app_produces: list of content types the application can return by default
        :type app_produces: list
        :param app_consumes: list of content types the application consumes by default
        :type app_consumes: list
        :param path_parameters: Parameters defined in the path level
        :type path_parameters: list
        :param app_security: list of security rules the application uses by default
        :type app_security: list
        :param security_schemes: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_schemes: dict
        :param definitions: `Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject>`_
        :type definitions: dict
        :param validate_responses: True enables validation. Validation errors generate HTTP 500 responses.
        :type validate_responses: bool
        :param strict_validation: True enables validation on invalid request parameters
        :type strict_validation: bool
        :param randomize_endpoint: number of random characters to append to operation name
        :type randomize_endpoint: integer
        :param validator_map: Custom validators for the types "parameter", "body" and "response".
        :type validator_map: dict
        :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended
            to any shadowed built-ins
        :type pythonic_params: bool
        :param uri_parser_class: class to use for uri parsing
        :type uri_parser_class: AbstractURIParser
        """
        uri_parser_class = uri_parser_class or Swagger2URIParser

        self._router_controller = operation.get("x-swagger-router-controller")

        super().__init__(
            api=api,
            method=method,
            path=path,
            operation=operation,
            resolver=resolver,
            app_security=app_security,
            security_schemes=security_schemes,
            validate_responses=validate_responses,
            strict_validation=strict_validation,
            randomize_endpoint=randomize_endpoint,
            validator_map=validator_map,
            pythonic_params=pythonic_params,
            uri_parser_class=uri_parser_class,
        )

        self._produces = operation.get("produces", app_produces)
        self._consumes = operation.get("consumes", app_consumes)

        self.definitions = definitions or {}

        self._parameters = operation.get("parameters", [])
        if path_parameters:
            self._parameters += path_parameters

        self._responses = operation.get("responses", {})
        logger.debug(self._responses)

        logger.debug("consumes: %s", self.consumes)
        logger.debug("produces: %s", self.produces)

    @classmethod
    def from_spec(cls, spec, api, path, method, resolver, *args, **kwargs):
        return cls(
            api,
            method,
            path,
            spec.get_operation(path, method),
            resolver=resolver,
            path_parameters=spec.get_path_params(path),
            app_produces=spec.produces,
            app_consumes=spec.consumes,
            app_security=spec.security,
            security_schemes=spec.security_schemes,
            definitions=spec.definitions,
            *args,
            **kwargs,
        )

    @property
    def parameters(self):
        return self._parameters

    @property
    def consumes(self):
        return self._consumes

    @property
    def produces(self):
        return self._produces

    def get_path_parameter_types(self):
        types = {}
        path_parameters = (p for p in self.parameters if p["in"] == "path")
        for path_defn in path_parameters:
            if path_defn.get("type") == "string" and path_defn.get("format") == "path":
                # path is special case for type 'string'
                path_type = "path"
            else:
                path_type = path_defn.get("type")
            types[path_defn["name"]] = path_type
        return types

    def with_definitions(self, schema):
        if "schema" in schema:
            schema["schema"]["definitions"] = self.definitions
        return schema

    def response_schema(self, status_code=None, content_type=None):
        response_definition = self.response_definition(status_code, content_type)
        return self.with_definitions(response_definition.get("schema", {}))

    def example_response(self, status_code=None, *args, **kwargs):
        """
        Returns example response from spec
        """
        # simply use the first/lowest status code, this is probably 200 or 201
        status_code = status_code or sorted(self._responses.keys())[0]
        examples_path = [str(status_code), "examples"]
        schema_example_path = [str(status_code), "schema", "example"]
        schema_path = [str(status_code), "schema"]

        try:
            status_code = int(status_code)
        except ValueError:
            status_code = 200
        try:
            return (
                list(deep_get(self._responses, examples_path).values())[0],
                status_code,
            )
        except KeyError:
            pass
        try:
            return (deep_get(self._responses, schema_example_path), status_code)
        except KeyError:
            pass

        try:
            return (
                self._nested_example(deep_get(self._responses, schema_path)),
                status_code,
            )
        except KeyError:
            return (None, status_code)

    def _nested_example(self, schema):
        try:
            return schema["example"]
        except KeyError:
            pass
        try:
            # Recurse if schema is an object
            return {
                key: self._nested_example(value)
                for (key, value) in schema["properties"].items()
            }
        except KeyError:
            pass
        try:
            # Recurse if schema is an array
            return [self._nested_example(schema["items"])]
        except KeyError:
            raise

    def body_schema(self, content_type: str = None) -> dict:
        """
        The body schema definition for this operation.
        """
        body_definition = self.body_definition(content_type)
        return self.with_definitions(body_definition).get("schema", {})

    def body_definition(self, content_type: str = None) -> dict:
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**

        :rtype: dict
        """
        if content_type in FORM_CONTENT_TYPES:
            form_parameters = [p for p in self.parameters if p["in"] == "formData"]
            body_definition = self._transform_form(form_parameters)
        else:
            body_parameters = [p for p in self.parameters if p["in"] == "body"]
            if len(body_parameters) > 1:
                raise InvalidSpecification(
                    "{method} {path} There can be one 'body' parameter at most".format(
                        method=self.method, path=self.path
                    )
                )
            body_definition = body_parameters[0] if body_parameters else {}
        return body_definition

    def _transform_form(self, form_parameters: t.List[dict]) -> dict:
        """Translate Swagger2 form parameters into OpenAPI 3 jsonschema spec."""
        properties = {}
        required = []
        encoding = {}

        for param in form_parameters:
            prop = {}

            if param["type"] == "file":
                prop.update(
                    {
                        "type": "string",
                        "format": "binary",
                    }
                )
            else:
                prop["type"] = param["type"]

                format_ = param.get("format")
                if format_ is not None:
                    prop["format"] = format_

            default = param.get("default")
            if default is not None:
                prop["default"] = default

            nullable = param.get("x-nullable")
            if nullable is not None:
                prop["nullable"] = nullable

            if param["type"] == "array":
                prop["items"] = param.get("items", {})

                collection_format = param.get("collectionFormat", "csv")
                try:
                    encoding[param["name"]] = COLLECTION_FORMAT_MAPPING[
                        collection_format
                    ]
                except KeyError:
                    raise InvalidSpecification(
                        f"The collection format ({collection_format}) is not supported by "
                        f"Connexion as it cannot be mapped to OpenAPI 3."
                    )

            properties[param["name"]] = prop

            if param.get("required", False):
                required.append(param["name"])

        definition: t.Dict[str, t.Any] = {
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": not self.strict_validation,
            }
        }

        if encoding:
            definition["encoding"] = encoding

        return definition

    def _get_query_arguments(self, query, arguments, has_kwargs, sanitize):
        query_defns = {p["name"]: p for p in self.parameters if p["in"] == "query"}
        default_query_params = {
            k: v["default"] for k, v in query_defns.items() if "default" in v
        }
        query_arguments = deepcopy(default_query_params)
        query_arguments.update(query)
        return self._query_args_helper(
            query_defns, query_arguments, arguments, has_kwargs, sanitize
        )

    def _get_body_argument(self, body, arguments, has_kwargs, sanitize):
        kwargs = {}
        body_parameters = [p for p in self.parameters if p["in"] == "body"] or [{}]
        if body is None:
            body = deepcopy(body_parameters[0].get("schema", {}).get("default"))
        body_name = sanitize(body_parameters[0].get("name"))

        form_defns = {p["name"]: p for p in self.parameters if p["in"] == "formData"}

        default_form_params = {
            k: v["default"] for k, v in form_defns.items() if "default" in v
        }

        # Add body parameters
        if body_name:
            if not has_kwargs and body_name not in arguments:
                logger.debug("Body parameter '%s' not in function arguments", body_name)
            else:
                logger.debug("Body parameter '%s' in function arguments", body_name)
                kwargs[body_name] = body

        # Add formData parameters
        form_arguments = deepcopy(default_form_params)
        if form_defns and body:
            form_arguments.update(body)
        for key, value in form_arguments.items():
            sanitized_key = sanitize(key)
            if not has_kwargs and sanitized_key not in arguments:
                logger.debug(
                    "FormData parameter '%s' (sanitized: '%s') not in function arguments",
                    key,
                    sanitized_key,
                )
            else:
                logger.debug(
                    "FormData parameter '%s' (sanitized: '%s') in function arguments",
                    key,
                    sanitized_key,
                )
                try:
                    form_defn = form_defns[key]
                except KeyError:  # pragma: no cover
                    logger.error(
                        "Function argument '%s' (non-sanitized: %s) not defined in specification",
                        key,
                        sanitized_key,
                    )
                else:
                    kwargs[sanitized_key] = self._get_val_from_param(value, form_defn)
        return kwargs

    def _get_val_from_param(self, value, query_defn):
        if is_nullable(query_defn) and is_null(value):
            return None

        query_schema = query_defn

        if query_schema["type"] == "array":
            return [make_type(part, query_defn["items"]["type"]) for part in value]
        else:
            return make_type(value, query_defn["type"])
