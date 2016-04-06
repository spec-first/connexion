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

import functools
import logging
import os

import requests
from flask import request

from ..problem import problem

logger = logging.getLogger('connexion.api.security')

# use connection pool for OAuth tokeninfo
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)


def get_tokeninfo_url(security_definition):
    '''
    :type security_definition: dict
    :rtype: str

    >>> get_tokeninfo_url({'x-tokenInfoUrl': 'foo'})
    'foo'
    '''
    token_info_url = (security_definition.get('x-tokenInfoUrl') or
                      os.environ.get('TOKENINFO_URL'))
    return token_info_url


def security_passthrough(function):
    """
    :type function: types.FunctionType
    :rtype: types.FunctionType
    """
    return function


def verify_oauth(token_info_url, allowed_scopes, function):
    """
    Decorator to verify oauth

    :param token_info_url: Url to get information about the token
    :type token_info_url: str
    :param allowed_scopes: Set with scopes that are allowed to access the endpoint
    :type allowed_scopes: set
    :type function: types.FunctionType
    :rtype: types.FunctionType
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug("%s Oauth verification...", request.url)
        authorization = request.headers.get('Authorization')  # type: str
        if not authorization:
            logger.info("... No auth provided. Aborting with 401.")
            return problem(401, 'Unauthorized', "No authorization token provided")
        else:
            try:
                _, token = authorization.split()  # type: str, str
            except ValueError:
                return problem(401, 'Unauthorized', 'Invalid authorization header')
            logger.debug("... Getting token '%s' from %s", token, token_info_url)
            token_request = session.get(token_info_url, params={'access_token': token}, timeout=5)
            logger.debug("... Token info (%d): %s", token_request.status_code, token_request.text)
            if not token_request.ok:
                return problem(401, 'Unauthorized', "Provided oauth token is not valid")
            token_info = token_request.json()  # type: dict
            user_scopes = set(token_info['scope'])
            scopes_intersection = user_scopes & allowed_scopes
            logger.debug("... Scope intersection: %s", scopes_intersection)
            if not scopes_intersection:
                logger.info("... User scopes (%s) don't include one of the allowed scopes (%s). Aborting with 401.",
                            user_scopes, allowed_scopes)
                return problem(403, 'Forbidden', "Provided token doesn't have the required scope")
            logger.info("... Token authenticated.")
            request.user = token_info.get('uid')
            request.token_info = token_info
        return function(*args, **kwargs)

    return wrapper
