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

from flask import request
import functools
import logging
import requests
from ..problem import problem

logger = logging.getLogger('connexion.api.security')

# use connection pool for OAuth tokeninfo
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)


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


def verify_gitkit(gitkit_config, cookie_name, function):
    """
    Decorator to verify oauth

    :param gitkit_config: Path to Google Identity Toolkit Configuration
    :type gitkit_config: str
    :param cookie_name: Name of the token cookie
    :type cookie_name: str
    :type function: types.FunctionType
    :rtype: types.FunctionType
    """
    try:
        from identitytoolkit import gitkitclient
    except ImportError:
        logger.error('Unable to find gitkit module!')

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return problem(401, 'Unauthorized', "gitkit module not found")
        return wrapper

    gitkit_instance = gitkitclient.GitkitClient.FromConfigFile(gitkit_config)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug("%s Gitkit verification...", request.url)
        gtoken = request.cookies.get(cookie_name)  # type: str
        if not gtoken:
            logger.error("... No auth provided. Aborting with 401.")
            return problem(401, 'Unauthorized', "No authorization token provided")
        else:
            logger.debug("... Getting token '%s' from %s", gtoken, cookie_name)
            gitkit_user = gitkit_instance.VerifyGitkitToken(gtoken)
            if gitkit_user is None:
                return problem(401, 'Unauthorized', "Provided gitkit token is not valid")
            logger.debug("... Token info (%d): %s", gitkit_user.user_id, str(gitkit_user.ToRequest()))
            logger.info("... Token authenticated.")
            request.user = gitkit_user.email
            request.gitkit = gitkit_user
        return function(*args, **kwargs)

    return wrapper
