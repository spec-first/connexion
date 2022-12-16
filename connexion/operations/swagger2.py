"""
This module defines a Swagger2Operation class, a Connexion operation specific for Swagger 2 specs.
"""

import logging
import typing as t

from connexion.exceptions import InvalidSpecification
from connexion.http_facts import FORM_CONTENT_TYPES
from connexion.operations.abstract import AbstractOperation
from connexion.uri_parsing import Swagger2URIParser
from connexion.utils import deep_get

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
        randomize_endpoint=None,
        pythonic_params=False,
        uri_parser_class=None,
        parameter_to_arg=None,
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
        :param randomize_endpoint: number of random characters to append to operation name
        :type randomize_endpoint: integer
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
            randomize_endpoint=randomize_endpoint,
            pythonic_params=pythonic_params,
            uri_parser_class=uri_parser_class,
            parameter_to_arg=parameter_to_arg,
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

    def body_name(self, content_type: str = None) -> str:
        return self.body_definition(content_type).get("name", "body")

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
        # TODO: cache
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
            body_parameter = body_parameters[0] if body_parameters else {}
            body_definition = self._transform_json(body_parameter)
        return body_definition

    def _transform_json(self, body_parameter: dict) -> dict:
        """Translate Swagger2 json parameters into OpenAPI 3 jsonschema spec."""
        nullable = body_parameter.get("x-nullable")
        if nullable is not None:
            body_parameter["schema"]["nullable"] = nullable
        return body_parameter

    def _transform_form(self, form_parameters: t.List[dict]) -> dict:
        """Translate Swagger2 form parameters into OpenAPI 3 jsonschema spec."""
        properties = {}
        defaults = {}
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
                defaults[param["name"]] = default

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
                "default": defaults,
                "required": required,
            }
        }

        if encoding:
            definition["encoding"] = encoding

        return definition
