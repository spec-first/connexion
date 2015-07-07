"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

# Decorator to validate requests
from flask import abort, request
import logging
import functools
import requests
import types

logger = logging.getLogger('connexion.decorators.parameters')


# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': float,
            'string': str,
            'boolean': bool}  # map of swagger types to python types

DEFINITIONS = {'new_stack': {'required': ['image_version', 'keep_stacks', 'new_traffic', 'senza_yaml'],
                             'type': 'object',
                             'properties': {'keep_stacks': {'type': 'integer',
                                                            'description':
                                                                'Number of older stacks to keep'},
                                            'image_version': {'type': 'string',
                                                              'description':
                                                                  'Docker image version to deploy'},
                                            'senza_yaml': {'type': 'string',
                                                           'description': 'YAML to provide to senza'},
                                            'new_traffic': {'type': 'integer',
                                                            'description':
                                                                'Percentage of the traffic'}}}}


def verify_request_schema(definition: dict, function: types.FunctionType) -> types.FunctionType:
    """
    Decorator to verify oauth
    """
    required = definition.get('required', [])

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug("%s Verifying request schema...", request.url, extra={'url': request.url})
        json_request = request.json()  # type: dict
        for key in required:
            if key not in json_request:
                logger.error("... missing key '%s'", key, extra={'url': request.url,
                                                                 'request_keys': json_request.keys()})
                abort(400)

        return function(*args, **kwargs)

    return wrapper
