# Decorators to change the return type of endpoints
import functools
import logging

from jsonschema import ValidationError

from ..exceptions import (NonConformingResponseBody,
                          NonConformingResponseHeaders)
from ..problem import problem
from ..utils import all_json
from .decorator import BaseDecorator
from .validation import ResponseBodyValidator

logger = logging.getLogger('connexion.decorators.response')


class ResponseValidator(BaseDecorator):
    def __init__(self, operation,  mimetype):
        """
        :type operation: Operation
        :type mimetype: str
        """
        self.operation = operation
        self.mimetype = mimetype

    def validate_response(self, data, status_code, headers, url):
        """
        Validates the Response object based on what has been declared in the specification.
        Ensures the response body matches the declated schema.
        :type data: dict
        :type status_code: int
        :type headers: dict
        :rtype bool | None
        """
        response_definitions = self.operation.operation["responses"]
        response_definition = response_definitions.get(str(status_code), {})
        response_definition = self.operation.resolve_reference(response_definition)
        # TODO handle default response definitions

        if self.is_json_schema_compatible(response_definition):
            schema = response_definition.get("schema")
            v = ResponseBodyValidator(schema)
            try:
                data = self.operation.json_loads(data)
                v.validate_schema(data, url)
            except ValidationError as e:
                raise NonConformingResponseBody(message=str(e))

        if response_definition and response_definition.get("headers"):
            # converting to set is needed to support python 2.7
            response_definition_header_keys = set(response_definition.get("headers").keys())
            header_keys = set(headers.keys())
            missing_keys = response_definition_header_keys - header_keys
            if missing_keys:
                pretty_list = ', '.join(missing_keys)
                msg = ("Keys in header don't match response specification. "
                       "Difference: {0}").format(pretty_list)
                raise NonConformingResponseHeaders(message=msg)
        return True

    def is_json_schema_compatible(self, response_definition):
        """
        Verify if the specified operation responses are JSON schema
        compatible.

        All operations that specify a JSON schema and have content
        type "application/json" or "text/plain" can be validated using
        json_schema package.

        :type response_definition: dict
        :rtype bool
        """
        if not response_definition:
            return False
        return ('schema' in response_definition and
                (all_json([self.mimetype]) or self.mimetype == 'text/plain'))

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        @functools.wraps(function)
        def wrapper(request):
            response = function(request)
            try:
                self.validate_response(
                    response.get_data(), response.status_code,
                    response.headers, request.url)

            except (NonConformingResponseBody, NonConformingResponseHeaders) as e:
                response = problem(500, e.reason, e.message)
                return self.operation.api.get_response(response)

            return response

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<ResponseValidator>'
