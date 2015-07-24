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
import logging
import numbers
import re
import types

from connexion.utils import parse_datetime
from connexion.problem import problem

logger = logging.getLogger('connexion.decorators.parameters')


# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': numbers.Number,
            'string': str,
            'boolean': bool,
            'array': list,
            'object': dict}  # map of swagger types to python types


FORMAT_MAP = {('string', 'date-time'): parse_datetime}


def validate_format(schema, data):
    schema_type = schema.get('type')
    schema_format = schema.get('format')
    func = FORMAT_MAP.get((schema_type, schema_format))
    if func:
        try:
            func(data)
        except:
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


VALIDATORS = [validate_format, validate_pattern, validate_minimum, validate_maximum]


class RequestBodyValidator:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, function: types.FunctionType) -> types.FunctionType:
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

    def validate_schema(self, data, schema) -> flask.Response:
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
