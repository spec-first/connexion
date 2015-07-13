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

from flask import abort, request
import functools
import logging
import requests
import types

from connexion.problem import problem


logger = logging.getLogger('connexion.api.security')


def security_passthrough(function: types.FunctionType) -> types.FunctionType:
    return function


def verify_oauth(token_info_url: str, allowed_scopes: set, function: types.FunctionType) -> types.FunctionType:
    """
    Decorator to verify oauth
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug("%s Oauth verification...", request.url)
        authorization = request.headers.get('Authorization')
        if authorization is None:
            logger.error("... No auth provided. Aborting with 401.")
            return problem(401, 'Unauthorized', "No authorization token provided")
        else:
            _, token = authorization.split()
            logger.debug("... Getting token '%s' from %s", token, token_info_url)
            token_request = requests.get(token_info_url, params={'access_token': token})
            logger.debug("... Token info (%d): %s", token_request.status_code, token_request.text)
            if not token_request.ok:
                return problem(401, 'Unauthorized', "Provided oauth token is not valid")
            token_info = token_request.json()
            user_scopes = set(token_info['scope'])
            scopes_intersection = user_scopes & allowed_scopes
            logger.debug("... Scope intersection: %s", scopes_intersection)
            if not scopes_intersection:
                logger.error("... User scopes (%s) don't include one of the allowed scopes (%s). Aborting with 401.",
                             user_scopes, allowed_scopes)
                return problem(403, 'Forbidden', "Provided token doesn't have the required scope")
            logger.info("... Token authenticated.")
        return function(*args, **kwargs)

    return wrapper
