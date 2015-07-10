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
import types

from connexion.problem import problem

logger = logging.getLogger('connexion.decorators.parameters')


# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': numbers.Number,
            'string': str,
            'boolean': bool}  # map of swagger types to python types


def validate_schema(data, schema) -> flask.Response:
    schema_type = schema.get('type')
    log_extra = {'url': flask.request.url, 'schema_type': schema_type}

    if schema_type == 'array':
        if not isinstance(data, list):
            logger.error("Wrong data type, expected 'list' got '%s'", type(data), extra=log_extra)
            return problem(400, 'Bad Request', "Wrong type, expected 'array' got '{}'".format(type(data)))
        for item in data:
            validate_schema(item, schema.get('items'))

    if schema_type == 'object':
        if not isinstance(data, dict):
            logger.error("Wrong data type, expected 'dict' got '%s'", type(data), extra=log_extra)
            return problem(400, 'Bad Request', "Wrong type, expected 'object' got '{}'".format(type(data)))

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
            key_properties = schema['properties'].get(key)
            if key_properties:
                expected_type = TYPE_MAP.get(key_properties['type'])
                if expected_type and not isinstance(data[key], expected_type):
                    logger.error("'%s' is not a '%s'", key, expected_type)
                    return problem(400, 'Bad Request', "Missing parameter '{}'".format(required_key))


class RequestBodyValidator:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, function: types.FunctionType) -> types.FunctionType:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = flask.request.json

            logger.debug("%s validating schema...", flask.request.url)
            error = validate_schema(data, self.schema)
            if error:
                return error

            response = function(*args, **kwargs)
            return response

        return wrapper
