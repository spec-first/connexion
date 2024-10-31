"""
This module defines an AbstractOperation class which implements an abstract Operation interface
and functionality shared between Swagger 2 and OpenAPI 3 specifications.
"""

import abc
import logging
import typing as t

from connexion.utils import all_json

logger = logging.getLogger("connexion.operations.abstract")

DEFAULT_MIMETYPE = "application/json"


class AbstractOperation(metaclass=abc.ABCMeta):

    """
    An API routes requests to an Operation by a (path, method) pair.
    The operation uses a resolver to resolve its handler function.
    We use the provided spec to do a bunch of heavy lifting before
    (and after) we call security_schemes handler.
    The registered handler function ends up looking something like::

        @secure_endpoint
        @validate_inputs
        @deserialize_function_inputs
        @serialize_function_outputs
        @validate_outputs
        def user_provided_handler_function(important, stuff):
            if important:
                serious_business(stuff)
    """

    def __init__(
        self,
        method,
        path,
        operation,
        resolver,
        app_security=None,
        security_schemes=None,
        randomize_endpoint=None,
        uri_parser_class=None,
    ):
        """
        :param method: HTTP method
        :type method: str
        :param path:
        :type path: str
        :param operation: swagger operation object
        :type operation: dict
        :param resolver: Callable that maps operationID to a function
        :param app_security: list of security rules the application uses by default
        :type app_security: list
        :param security_schemes: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_schemes: dict
        :param randomize_endpoint: number of random characters to append to operation name
        :type randomize_endpoint: integer
        :param uri_parser_class: class to use for uri parsing
        :type uri_parser_class: AbstractURIParser
        """
        self._method = method
        self._path = path
        self._operation = operation
        self._resolver = resolver
        self._security = operation.get("security", app_security)
        self._security_schemes = security_schemes
        self._uri_parser_class = uri_parser_class
        self._randomize_endpoint = randomize_endpoint
        self._operation_id = self._operation.get("operationId")

        self._resolution = resolver.resolve(self)
        self._operation_id = self._resolution.operation_id

        self._responses = self._operation.get("responses", {})

    @classmethod
    @abc.abstractmethod
    def from_spec(cls, spec, *args, path, method, resolver, **kwargs):
        pass

    @property
    def method(self):
        """
        The HTTP method for this operation (ex. GET, POST)
        """
        return self._method

    @property
    def request_body(self):
        """The request body for this operation"""

    @property
    def is_request_body_defined(self) -> bool:
        """Whether the request body is defined for this operation"""
        return self.request_body != {}

    @property
    def path(self):
        """
        The path of the operation, relative to the API base path
        """
        return self._path

    @property
    def security(self):
        return self._security

    @property
    def security_schemes(self):
        return self._security_schemes

    @property
    def responses(self):
        """
        Returns the responses for this operation
        """
        return self._responses

    @property
    def operation_id(self):
        """
        The operation id used to identify the operation internally to the app
        """
        return self._operation_id

    @property
    def randomize_endpoint(self):
        """
        number of random digits to generate and append to the operation_id.
        """
        return self._randomize_endpoint

    @property
    def router_controller(self):
        """
        The router controller to use (python module where handler functions live)
        """
        return self._router_controller

    @property
    @abc.abstractmethod
    def parameters(self):
        """
        Returns the parameters for this operation
        """

    @property
    @abc.abstractmethod
    def produces(self):
        """
        Content-Types that the operation produces
        """

    @property
    @abc.abstractmethod
    def consumes(self):
        """
        Content-Types that the operation consumes
        """

    @abc.abstractmethod
    def body_name(self, content_type: str) -> str:
        """
        Name of the body in the spec.
        """

    @abc.abstractmethod
    def body_schema(self, content_type: t.Optional[str] = None) -> dict:
        """
        The body schema definition for this operation.
        """

    @abc.abstractmethod
    def body_definition(self, content_type: t.Optional[str] = None) -> dict:
        """
        The body definition for this operation.
        :rtype: dict
        """

    def response_definition(self, status_code=None, content_type=None):
        """
        response definition for this endpoint
        """
        response_definition = self.responses.get(
            str(status_code), self.responses.get("default", {})
        )
        return response_definition

    @abc.abstractmethod
    def response_schema(self, status_code=None, content_type=None):
        """
        response schema for this endpoint
        """

    @abc.abstractmethod
    def example_response(self, status_code=None, content_type=None):
        """
        Returns an example from the spec
        """

    @abc.abstractmethod
    def get_path_parameter_types(self):
        """
        Returns the types for parameters in the path
        """

    @abc.abstractmethod
    def with_definitions(self, schema):
        """
        Returns the given schema, but with the definitions from the spec
        attached. This allows any remaining references to be resolved by a
        validator (for example).
        """

    def get_mimetype(self):
        """
        If the endpoint has no 'produces' then the default is
        'application/json'.

        :rtype str
        """
        # TODO: don't default
        if all_json(self.produces):
            try:
                return self.produces[0]
            except IndexError:
                return DEFAULT_MIMETYPE
        elif len(self.produces) == 1:
            return self.produces[0]
        else:
            return DEFAULT_MIMETYPE

    @property
    def uri_parser_class(self):
        """
        The uri parser class for this operation.
        """
        return self._uri_parser_class

    @property
    def function(self):
        """
        Resolved function.

        :rtype: types.FunctionType
        """
        return self._resolution.function
