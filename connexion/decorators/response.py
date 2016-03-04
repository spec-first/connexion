"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

# Decorators to change the return type of endpoints
import functools
import logging
import ast
from ..exceptions import NonConformingResponse
from ..problem import problem
from .validation import RequestBodyValidator
from .decorator import BaseDecorator


logger = logging.getLogger('connexion.decorators.response')


class ResponseValidator(BaseDecorator):
    def __init__(self, operation={},  mimetype='text/plain'):
        """
        :type operation: Operation
        :type mimetype: str
        """
        self.operation = operation
        self.mimetype = mimetype

    def validate_response(self, data, status_code, headers, mimetype):
        """
        Validates the Response object based on what has been declared in the specification.
        Ensures the response body matches the declated schema.
        :type data: dict
        :type status_code: int
        :type mimetype: str
        :rtype bool | None
        """
        response_definitions = self.operation.operation["responses"]
        response_definition = response_definitions.get(str(status_code), {})
        response_definition = self.operation.resolve_reference(response_definition)
        # TODO handle default response definitions

        if response_definition and response_definition.get("schema"):
            schema = response_definition.get("schema")
            v = RequestBodyValidator(schema)
            error = v.validate_schema(data, schema)
            if error:
                if isinstance(error.response, list) and len(error.response) > 0:
                    error_dict = ast.literal_eval(error.response[0])
                    logger.debug('Validation error in response body was:\n{0}'.format(error_dict["detail"]))
                raise NonConformingResponse("Response body does not conform to specification")

        if response_definition and response_definition.get("headers"):
            if not all(item in headers.keys() for item in response_definition.get("headers").keys()):
                raise NonConformingResponse("Response headers do not conform to specification")
        return True

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            result = function(*args, **kwargs)
            try:
                data, status_code, headers = self.get_full_response(result)
                self.validate_response(data, status_code, headers, self.mimetype)
            except NonConformingResponse as e:
                return problem(500, 'Internal Server Error', e.reason)
            return result

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<ResponseValidator>'
