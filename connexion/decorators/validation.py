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
import logging
import functools
import numbers
import types

from flask import abort


logger = logging.getLogger('connexion.decorators.parameters')


# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': numbers.Number,
            'string': str,
            'boolean': bool}  # map of swagger types to python types


def validate_schema(data, schema):
    schema_type = schema.get('type')
    if schema_type == 'array':
        if not isinstance(data, list):
            raise abort(400)
        for item in data:
            validate_schema(item, schema.get('items'))

    if schema_type == 'object':
        if not isinstance(data, dict):
            raise abort(400)

        # verify if required keys are present
        required_keys = schema.get('required', [])
        logger.debug('... required keys: %s', required_keys)
        for required_key in schema.get('required', required_keys):
            if required_key not in data:
                logger.debug("... '%s' missing", required_key)
                raise abort(400)

        # verify if value types are correct
        for key in data.keys():
            key_properties = schema['properties'].get(key)
            if key_properties:
                expected_type = TYPE_MAP.get(key_properties['type'])
                if expected_type and not isinstance(data[key], expected_type):
                    logger.debug("... '%s' is not a '%s'", key, expected_type)
                    raise abort(400)


class RequestBodyValidator:

    def __init__(self, schema):
        self.schema = schema

    def __call__(self, function: types.FunctionType) -> types.FunctionType:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = flask.request.json
            logger.debug("%s validating schema...", flask.request.url)
            validate_schema(data, self.schema)
            response = function(*args, **kwargs)
            return response

        return wrapper
