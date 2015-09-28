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


def validate_type(schema, data, parameter_type, parameter_name=None):
    schema_type = schema.get('type')
    parameter_name = parameter_name if parameter_name else schema['name']
    expected_type = TYPE_VALIDATION_MAP.get(schema_type)
    if expected_type:
        try:
            return expected_type(data), None
        except:
            return None, "Wrong type, expected '{}' for {} parameter '{}'".format(
                schema_type, parameter_type, parameter_name)
    return data, None


def validate_format(schema, data):
    schema_type = schema.get('type')
    schema_format = schema.get('format')
    func = FORMAT_MAP.get((schema_type, schema_format))
    if func and not func(data):
        return "Invalid value, expected {} in '{}' format".format(schema_type, schema_format)


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
    col_map = {'csv':   ',',
               'ssv':   ' ',
               'tsv':   '\t',
               'pipes': '|',
               'multi': '&'}
    col_fmt = schema.get('collectionFormat', 'csv')
    delimiter = col_map.get(col_fmt)
    if not delimiter:
        logger.error("Unrecognized collectionFormat, cannot validate: %s", col_fmt)
        return
    if col_fmt == 'multi':
        logger.debug("collectionFormat 'multi' is not validated by Connexion")
        return
    subschema = schema.get('items')
    items = data.split(delimiter)
    for subval in items:
        converted_value, error = validate_type(subschema, subval, schema['in'], schema['name'])
        if error:
            return error
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
        schema_type = schema.get('type')
        log_extra = {'url': flask.request.url, 'schema_type': schema_type}

        expected_type = TYPE_MAP.get(schema_type)  # type: type
        actual_type = type(data)  # type: type
        if expected_type and not isinstance(data, expected_type):
            expected_type_name = expected_type.__name__
            actual_type_name = actual_type.__name__
            logger.error("'%s' is not a '%s'", data, expected_type_name)
            return problem(400, 'Bad Request',
                           "Wrong type, expected '{}' got '{}'".format(schema_type, actual_type_name))

        if schema_type == 'array':
            for item in data:
                error = self.validate_schema(item, schema.get('items'))
                if error:
                    return error
        elif schema_type == 'object':
            # verify if required keys are present
            required_keys = schema.get('required', [])
            logger.debug('... required keys: %s', required_keys)
            log_extra['required_keys'] = required_keys
            for required_key in schema.get('required', required_keys):
                if required_key not in data:
                    logger.error("Missing parameter '%s'", required_key, extra=log_extra)
                    return problem(400, 'Bad Request', "Missing parameter '{}'".format(required_key))

            # verify if value types are correct
            for key in data.keys():
                key_properties = schema.get('properties', {}).get(key)
                if key_properties:
                    error = self.validate_schema(data[key], key_properties)
                    if error:
                        return error
        else:
            for func in VALIDATORS:
                error = func(schema, data)
                if error:
                    return problem(400, 'Bad Request', error)


class ParameterValidator():
    def __init__(self, parameters):
        self.parameters = {k: list(g) for k, g in itertools.groupby(parameters, key=lambda p: p['in'])}

    def validate_parameter(self, parameter_type, value, param):
        if value is not None:
            converted_value, error = validate_type(param, value, parameter_type)
            if error:
                return error
            for func in VALIDATORS:
                error = func(param, converted_value)
                if error:
                    return error
        elif param.get('required'):
            return "Missing {} parameter '{}'".format(parameter_type, param['name'])

    def validate_query_parameter(self, param):
        '''
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        '''
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
