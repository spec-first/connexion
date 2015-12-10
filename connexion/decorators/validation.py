"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import flask
import functools
import itertools
import logging
import numbers
import re
import six
import strict_rfc3339
from jsonschema import validate, ValidationError

from ..problem import problem
from ..utils import validate_date, boolean

logger = logging.getLogger('connexion.decorators.validation')

# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': numbers.Number,
            'string': six.string_types[0],
            'boolean': bool,
            'array': list,
            'object': dict}  # map of swagger types to python types

TYPE_VALIDATION_MAP = {
    'integer': int,
    'number': float,
    'boolean': boolean
}

FORMAT_MAP = {('string', 'date-time'): strict_rfc3339.validate_rfc3339,
              ('string', 'date'): validate_date}


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


def validate_type(schema, data, parameter_type, parameter_name=None):
    schema_type = schema.get('type')
    parameter_name = parameter_name if parameter_name else schema['name']
    expected_type = TYPE_VALIDATION_MAP.get(schema_type)
    if expected_type:
        try:
            return expected_type(data)
        except ValueError:
            raise TypeValidationError(schema_type, parameter_type, parameter_name)
    return data


def validate_format(schema, data):
    schema_type = schema.get('type')
    schema_format = schema.get('format')
    func = FORMAT_MAP.get((schema_type, schema_format))
    if func and not func(data):
        return "Invalid value, expected {schema_type} in '{schema_format}' format".format(**locals())


def validate_pattern(schema, data):
    pattern = schema.get('pattern')
    # TODO: check Swagger pattern format
    if pattern is not None and not re.match(pattern, data):
        return 'Invalid value, pattern "{}" does not match'.format(pattern)


def validate_minimum(schema, data):
    minimum = schema.get('minimum')
    if minimum is not None and data < minimum:
        return 'Invalid value, must be at least {}'.format(minimum)


def validate_maximum(schema, data):
    maximum = schema.get('maximum')
    if maximum is not None and data > maximum:
        return 'Invalid value, must be at most {}'.format(maximum)


def validate_min_length(schema, data):
    minimum = schema.get('minLength')
    if minimum is not None and len(data) < minimum:
        return 'Length must be at least {}'.format(minimum)


def validate_max_length(schema, data):
    maximum = schema.get('maxLength')
    if maximum is not None and len(data) > maximum:
        return 'Length must be at most {}'.format(maximum)


def validate_enum(schema, data):
    enum_values = schema.get('enum')
    if enum_values is not None and data not in enum_values:
        return 'Enum value must be one of {}'.format(enum_values)


def validate_array(schema, data):
    if schema.get('type') != 'array' or not schema.get('items'):
        return
    col_map = {'csv': ',',
               'ssv': ' ',
               'tsv': '\t',
               'pipes': '|',
               'multi': '&'}
    col_fmt = schema.get('collectionFormat', 'csv')
    delimiter = col_map.get(col_fmt)
    if not delimiter:
        logger.debug("Unrecognized collectionFormat, cannot validate: %s", col_fmt)
        return
    if col_fmt == 'multi':
        logger.debug("collectionFormat 'multi' is not validated by Connexion")
        return
    subschema = schema.get('items')
    items = data.split(delimiter)
    for subval in items:
        try:
            converted_value = validate_type(subschema, subval, schema['in'], schema['name'])
        except TypeValidationError as e:
            return str(e)
        # Run each sub-item through the list of validators.
        for func in VALIDATORS:
            error = func(subschema, converted_value)
            if error:
                return error


VALIDATORS = [validate_format, validate_pattern,
              validate_minimum, validate_maximum,
              validate_min_length, validate_max_length,
              validate_enum, validate_array]


class RequestBodyValidator:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = flask.request.json

            logger.debug("%s validating schema...", flask.request.url)
            error = self.validate_schema(data, self.schema)
            if error:
                return error

            response = function(*args, **kwargs)
            return response

        return wrapper

    def validate_schema(self, data, schema):
        """
        :type schema: dict
        :rtype: flask.Response | None
        """
        try:
            validate(data, schema)
        except ValidationError as exception:
            return problem(400, 'Bad Request', str(exception))

        return None


class ParameterValidator():
    def __init__(self, parameters):
        self.parameters = {k: list(g) for k, g in itertools.groupby(parameters, key=lambda p: p['in'])}

    def validate_parameter(self, parameter_type, value, param):
        if value is not None:
            try:
                converted_value = validate_type(param, value, parameter_type)
            except TypeValidationError as e:
                return str(e)
            for func in VALIDATORS:
                error = func(param, converted_value)
                if error:
                    return error
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
