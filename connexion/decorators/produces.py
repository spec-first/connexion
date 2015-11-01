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
import datetime
import flask
import functools
import json
import logging
from ..exceptions import NonConformingResponse
from ..problem import problem
from .validation import RequestBodyValidator
import ast

logger = logging.getLogger('connexion.decorators.produces')

# special marker object to return empty content for any status code
# e.g. in app method do "return NoContent, 201"
NoContent = object()


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            if o.tzinfo:
                # eg: '2015-09-25T23:14:42.588601+00:00'
                return o.isoformat('T')
            else:
                # No timezone present - assume UTC.
                # eg: '2015-09-25T23:14:42.588601Z'
                return o.isoformat('T') + 'Z'

        if isinstance(o, datetime.date):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


class BaseSerializer:
    def __init__(self, mimetype='text/plain', operation={}):
        """
        :type mimetype: str
        :type operation: Operation
        """
        self.mimetype = mimetype
        self.operation = operation

    @staticmethod
    def get_full_response(data):
        """
        Gets Data. Status Code and Headers for response.
        If only body data is returned by the endpoint function, then the status code will be set to 200 and no headers
        will be added.
        If the returned object is a flask.Response then it will just pass the information needed to recreate it.

        :type data: flask.Response | (object, int) | (object, int, dict) | object
        :rtype: (object, int, dict)
        """
        url = flask.request.url
        logger.debug('Getting data and status code', extra={'data': data, 'data_type': type(data), 'url': url})
        status_code, headers = 200, {}
        if isinstance(data, flask.Response):
            data = data
            status_code = data.status_code
            headers = data.headers
        elif isinstance(data, tuple) and len(data) == 3:
            data, status_code, headers = data
        elif isinstance(data, tuple) and len(data) == 2:
            data, status_code = data
        logger.debug('Got data and status code (%d)', status_code, extra={'data': data,
                                                                          'data_type': type(data),
                                                                          'url': url})
        return data, status_code, headers

    @staticmethod
    def process_headers(response, headers):
        """
        A convenience function for updating the Response headers with any additional headers
        generated in the view. If more complex logic should be needed later then it can be handled here.

        :type response: flask.Response
        :type headers: dict
        :rtype flask.Response
        """
        if headers:
            for header, value in headers.items():
                response.headers[header] = value
        return response

    def get_as_type(self, data_string, schema_type, mimetype):
        """
        A function to convert the serialized response body back into its intended types for validation.
        If the schema is declared as an "object" and the mimetype is a form of JSON, then load as JSON.
        The string is tested in this order: json, boolean, float, integer - or return as string.

        :type data_string: string The response body as a string
        :type schema_type: dict The schema type declared in the spec for the response body
        :rtype dict | bool | float | int | str
        """
        if schema_type == "object" and "json" in mimetype:  # json
            return json.loads(data_string)
        if data_string[:1] == "[":  # array?
            try:
                return ast.literal_eval(data_string)
            except ValueError:
                pass
        if data_string.lower() == "true":  # boolean?
            return True
        elif data_string.lower() == "false":
            return False
        if "." in data_string:  # float?
            try:
                return float(data_string)
            except ValueError:
                pass
        try:  # integer?
            return int(data_string)
        except ValueError:
            pass
        return data_string  # leave as a string

    def validate_response(self, response, status_code, mimetype):
        """
        Validates the Response object based on what has been declared in the specification.
        Ensures the response body matches the declated schema.
        :type response: flask.Response
        :type status_code: int
        :type mimetype: str
        :rtype bool | None
        """
        response_definitions = self.operation.operation.get("responses", {})
        if not response_definitions:
            return response
        response_definition = response_definitions.get(status_code, {})
        # TODO handle default response definitions

        if response_definition and response_definition.get("schema"):
            schema = self.operation.resolve_reference(response_definition.get("schema"))
            data = self.get_as_type(response.get_data(), schema.get("type"), mimetype)
            v = RequestBodyValidator(schema)
            error = v.validate_schema(data, schema)
            if error:
                raise NonConformingResponse("Response body does not conform to specification")

        if response_definition and response_definition.get("headers"):
            if not all(item in response.headers.keys() for item in response_definition.get("headers").keys()):
                raise NonConformingResponse("Response headers do not conform to specification")
        return True

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        return function

    def __repr__(self):
        """
        :rtype: str
        """
        return '<BaseSerializer: {}>'.format(self.mimetype)


class Produces(BaseSerializer):
    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            url = flask.request.url
            data, status_code, headers = self.get_full_response(function(*args, **kwargs))
            logger.debug((data, status_code, headers))
            logger.debug('Returning %s', url, extra={'url': url, 'mimetype': self.mimetype})
            if isinstance(data, flask.Response):  # if the function returns a Response object don't change it
                logger.debug('Endpoint returned a Flask Response', extra={'url': url, 'mimetype': data.mimetype})
                return data

            data = str(data)
            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            response = self.process_headers(response, headers)

            try:
                self.validate_response(response, status_code, self.mimetype)
            except NonConformingResponse as e:
                return problem(500, 'Internal Server Error', e.reason)

            return response, status_code

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Produces: {}>'.format(self.mimetype)


class Jsonifier(BaseSerializer):
    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            url = flask.request.url
            logger.debug('Jsonifing %s', url, extra={'url': url, 'mimetype': self.mimetype})
            data, status_code, headers = self.get_full_response(function(*args, **kwargs))
            if isinstance(data, flask.Response):  # if the function returns a Response object don't change it
                logger.debug('Endpoint returned a Flask Response', extra={'url': url, 'mimetype': data.mimetype})
                return data
            elif data is NoContent:
                return '', status_code
            elif status_code == 204:
                logger.debug('Endpoint returned an empty response (204)', extra={'url': url, 'mimetype': self.mimetype})
                return '', 204

            data = json.dumps(data, indent=2, cls=JSONEncoder)
            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            response = self.process_headers(response, headers)

            try:
                self.validate_response(response, status_code, self.mimetype)
            except NonConformingResponse as e:
                return problem(500, 'Internal Server Error', e.reason)

            return response, status_code

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Jsonifier: {}>'.format(self.mimetype)
