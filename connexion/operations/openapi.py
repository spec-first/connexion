"""
This module defines an OpenAPIOperation class, a Connexion operation specific for OpenAPI 3 specs.
"""

import logging

from connexion.datastructures import MediaTypeDict
from connexion.operations.abstract import AbstractOperation
from connexion.uri_parsing import OpenAPIURIParser
from connexion.utils import deep_get

logger = logging.getLogger("connexion.operations.openapi3")


class OpenAPIOperation(AbstractOperation):

    """
    A single API operation on a path.
    """

    def __init__(
        self,
        method,
        path,
        operation,
        resolver,
        path_parameters=None,
        app_security=None,
        security_schemes=None,
        components=None,
        randomize_endpoint=None,
        uri_parser_class=None,
    ):
        """
        This class uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.

        :param method: HTTP method
        :type method: str
        :param path:
        :type path: str
        :param operation: swagger operation object
        :type operation: dict
        :param resolver: Callable that maps operationID to a function
        :param path_parameters: Parameters defined in the path level
        :type path_parameters: list
        :param app_security: list of security rules the application uses by default
        :type app_security: list
        :param security_schemes: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_schemes: dict
        :param components: `Components Object
            <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md#componentsObject>`_
        :type components: dict
        :param randomize_endpoint: number of random characters to append to operation name
        :type randomize_endpoint: integer
        :param uri_parser_class: class to use for uri parsing
        :type uri_parser_class: AbstractURIParser
        """
        self.components = components or {}

        uri_parser_class = uri_parser_class or OpenAPIURIParser

        self._router_controller = operation.get("x-openapi-router-controller")

        super().__init__(
            method=method,
            path=path,
            operation=operation,
            resolver=resolver,
            app_security=app_security,
            security_schemes=security_schemes,
            randomize_endpoint=randomize_endpoint,
            uri_parser_class=uri_parser_class,
        )

        self._parameters = operation.get("parameters", [])
        if path_parameters:
            self._parameters += path_parameters

        self._responses = operation.get("responses", {})

        # TODO figure out how to support multiple mimetypes
        # NOTE we currently just combine all of the possible mimetypes,
        #      but we need to refactor to support mimetypes by response code
        response_content_types = []
        for _, defn in self._responses.items():
            response_content_types += defn.get("content", {}).keys()
        self._produces = response_content_types
        self._consumes = None

        logger.debug("consumes: %s" % self.consumes)
        logger.debug("produces: %s" % self.produces)

    @classmethod
    def from_spec(cls, spec, *args, path, method, resolver, **kwargs):
        return cls(
            method,
            path,
            spec.get_operation(path, method),
            resolver=resolver,
            path_parameters=spec.get_path_params(path),
            app_security=spec.security,
            security_schemes=spec.security_schemes,
            components=spec.components,
            *args,
            **kwargs,
        )

    @property
    def request_body(self):
        return self._operation.get("requestBody", {})

    @property
    def parameters(self):
        return self._parameters

    @property
    def consumes(self):
        if self._consumes is None:
            request_content = self.request_body.get("content", {})
            self._consumes = list(request_content.keys())
        return self._consumes

    @property
    def produces(self):
        return self._produces

    def with_definitions(self, schema: dict):
        if self.components:
            schema.setdefault("schema", {})
            schema["schema"]["components"] = self.components
        return schema

    def response_schema(self, status_code=None, content_type=None):
        response_definition = self.response_definition(status_code, content_type)
        content_definition = response_definition.get("content", response_definition)
        content_definition = content_definition.get(content_type, content_definition)
        if "schema" in content_definition:
            return self.with_definitions(content_definition).get("schema", {})
        return {}

    def example_response(self, status_code=None, content_type=None):
        """
        Returns example response from spec
        """
        # simply use the first/lowest status code, this is probably 200 or 201
        status_code = status_code or sorted(self._responses.keys())[0]

        content_type = content_type or self.get_mimetype()
        examples_path = [str(status_code), "content", content_type, "examples"]
        example_path = [str(status_code), "content", content_type, "example"]
        schema_example_path = [
            str(status_code),
            "content",
            content_type,
            "schema",
            "example",
        ]
        schema_path = [str(status_code), "content", content_type, "schema"]

        try:
            status_code = int(status_code)
        except ValueError:
            status_code = 200
        try:
            # TODO also use example header?
            return (
                list(deep_get(self._responses, examples_path).values())[0]["value"],
                status_code,
            )
        except (KeyError, IndexError):
            pass
        try:
            return (deep_get(self._responses, example_path), status_code)
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

    def get_path_parameter_types(self):
        types = {}
        path_parameters = (p for p in self.parameters if p["in"] == "path")
        for path_defn in path_parameters:
            path_schema = path_defn["schema"]
            if (
                path_schema.get("type") == "string"
                and path_schema.get("format") == "path"
            ):
                # path is special case for type 'string'
                path_type = "path"
            else:
                path_type = path_schema.get("type")
            types[path_defn["name"]] = path_type
        return types

    def body_name(self, _content_type: str) -> str:
        return self.request_body.get("x-body-name", "body")

    def body_schema(self, content_type: str = None) -> dict:
        """
        The body schema definition for this operation.
        """
        return self.body_definition(content_type).get("schema", {})

    def body_definition(self, content_type: str = None) -> dict:
        """
        The body complete definition for this operation.

        **There can be one "body" parameter at most.**
        """
        if self.request_body:
            if content_type is None:
                # TODO: make content type required
                content_type = self.consumes[0]
            if len(self.consumes) > 1:
                logger.warning(
                    "this operation accepts multiple content types, using %s",
                    content_type,
                )
            content_type_dict = MediaTypeDict(self.request_body.get("content", {}))
            res = content_type_dict.get(content_type, {})
            return self.with_definitions(res)
        return {}
