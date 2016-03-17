"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import copy
import flask
import functools
import itertools
import logging
from jsonschema import draft4_format_checker, validate, ValidationError

from ..problem import problem
from ..utils import boolean

logger = logging.getLogger('connexion.decorators.validation')

TYPE_MAP = {
    'integer': int,
    'number': float,
    'boolean': boolean
}


class TypeValidationError(Exception):
    def __init__(self, schema_type, parameter_type, parameter_name):
        """
        Exception raise when type validation fails

        :type schema_type: str
        :type parameter_type: str
        :type parameter_name: str
        :return:
        """
        self.schema_type = schema_type
        self.parameter_type = parameter_type
        self.parameter_name = parameter_name

    def __str__(self):
        msg = "Wrong type, expected '{schema_type}' for {parameter_type} parameter '{parameter_name}'"
        return msg.format(**vars(self))


def make_type(value, type):
    type_func = TYPE_MAP.get(type)  # convert value to right type
    return type_func(value)


def validate_type(param, value, parameter_type, parameter_name=None):
    param_type = param.get('type')
    parameter_name = parameter_name if parameter_name else param['name']
    if param_type == "array":  # then logic is more complex
        if param.get("collectionFormat") and param.get("collectionFormat") == "pipes":
            parts = value.split("|")
        else:  # default: csv
            parts = value.split(",")

        converted_parts = []
        for part in parts:
            try:
                converted = make_type(part, param["items"]["type"])
            except (ValueError, TypeError):
                converted = part
        converted_parts.append(converted)
        return converted_parts
    else:
        try:
            return make_type(value, param_type)
        except ValueError:
            raise TypeValidationError(param_type, parameter_type, parameter_name)
        except TypeError:
            return value


class RequestBodyValidator(object):
    def __init__(self, schema, has_default=False):
        """
        :param schema: The schema of the request body
        :param has_default: Flag to indicate if default value is present.
        """
        self.schema = schema
        self.has_default = schema.get('default', has_default)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = flask.request.json

            logger.debug("%s validating schema...", flask.request.url)
            error = self.validate_schema(data)
            if error and not self.has_default:
                return error

            response = function(*args, **kwargs)
            return response

        return wrapper

    def validate_schema(self, data):
        """
        :type schema: dict
        :rtype: flask.Response | None
        """
        try:
            validate(data, self.schema, format_checker=draft4_format_checker)
        except ValidationError as exception:
            return problem(400, 'Bad Request', str(exception.message))

        return None


class ParameterValidator(object):
    def __init__(self, parameters):
        self.parameters = {k: list(g) for k, g in itertools.groupby(parameters, key=lambda p: p['in'])}

    @staticmethod
    def validate_parameter(parameter_type, value, param):
        if value is not None:
            try:
                converted_value = validate_type(param, value, parameter_type)
            except TypeValidationError as e:
                return str(e)

            param = copy.deepcopy(param)
            if 'required' in param:
                del param['required']
            try:
                validate(converted_value, param, format_checker=draft4_format_checker)
            except ValidationError as exception:
                print(converted_value, type(converted_value), param.get('type'), param, '<--------------------------')
                return str(exception)

        elif param.get('required'):
            return "Missing {parameter_type} parameter '{param[name]}'".format(**locals())

    def validate_query_parameter(self, param):
        """
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        """
        val = flask.request.args.get(param['name'])
        return self.validate_parameter('query', val, param)

    def validate_path_parameter(self, args, param):
        val = args.get(param['name'].replace('-', '_'))
        return self.validate_parameter('path', val, param)

    def validate_header_parameter(self, param):
        val = flask.request.headers.get(param['name'])
        return self.validate_parameter('header', val, param)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            logger.debug("%s validating parameters...", flask.request.url)

            for param in self.parameters.get('query', []):
                error = self.validate_query_parameter(param)
                if error:
                    return problem(400, 'Bad Request', error)

            for param in self.parameters.get('path', []):
                error = self.validate_path_parameter(kwargs, param)
                if error:
                    return problem(400, 'Bad Request', error)

            for param in self.parameters.get('header', []):
                error = self.validate_header_parameter(param)
                if error:
                    return problem(400, 'Bad Request', error)

            response = function(*args, **kwargs)
            return response

        return wrapper
