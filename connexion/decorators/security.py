"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

# Authentication and authorization related decorators

import logging
import functools
import types

import flask
import requests


logger = logging.getLogger('connexion.api.security')


def verify_oauth(token_info_url: str, scope: list, function: types.FunctionType) -> types.FunctionType:
    """
    Decorator to verify oauth
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        authorization = flask.request.headers.get('Authorization')
        if authorization is None:
            logger.error('No auth provided')
            raise flask.abort(401)
        else:
            _, token = authorization.split()
            logger.error(token)
            token_request = requests.get(token_info_url, params={'access_token': token})
            logger.debug("Token verification (%d): %s", token_request.status_code, token_request.text)
            if not token_request.ok:
                raise flask.abort(401)
            # TODO verify scopes
        return function(*args, **kwargs)
    return wrapper
