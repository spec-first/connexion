# Authentication and authorization related decorators
import functools
import logging
import os
import textwrap

import requests

from connexion.utils import get_function_from_name

from ..exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem

logger = logging.getLogger('connexion.api.security')

# use connection pool for OAuth tokeninfo
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)


def get_tokeninfo_func(security_definition):
    """
    :type security_definition: dict
    :rtype: function

    >>> get_tokeninfo_url({'x-tokenInfoFunc': 'foo.bar>'})
    '<function foo.bar>'
    """
    token_info_func = (security_definition.get("x-tokenInfoFunc") or
                       os.environ.get('TOKENINFO_FUNC'))
    return get_function_from_name(token_info_func) if token_info_func else None


def get_tokeninfo_url(security_definition):
    """
    :type security_definition: dict
    :rtype: str

    >>> get_tokeninfo_url({'x-tokenInfoUrl': 'foo'})
    'foo'
    """
    token_info_url = (security_definition.get('x-tokenInfoUrl') or
                      os.environ.get('TOKENINFO_URL'))
    return token_info_url


def security_passthrough(function):
    """
    :type function: types.FunctionType
    :rtype: types.FunctionType
    """
    return function


def get_authorization_token(request):
    authorization = request.headers.get('Authorization')  # type: str
    if not authorization:
        logger.info("... No auth provided. Aborting with 401.")
        raise OAuthProblem(description='No authorization token provided')
    else:
        try:
            _, token = authorization.split()  # type: str, str
        except ValueError:
            raise OAuthProblem(description='Invalid authorization header')
    return token


def validate_token_info(token_info, allowed_scopes):
    """
    :param allowed_scopes:
    :param token_info: Dictionary containing the token_info
    :type token_info: dict
    :return: None
    """
    scope = token_info.get('scope') or token_info.get('scopes')
    if isinstance(scope, list):
        user_scopes = set(scope)
    else:
        user_scopes = set(scope.split())
    logger.debug("... Scopes required: %s", allowed_scopes)
    logger.debug("... User scopes: %s", user_scopes)
    if not allowed_scopes <= user_scopes:
        logger.info(textwrap.dedent("""
                    ... User scopes (%s) do not match the scopes necessary to call endpoint (%s).
                     Aborting with 403.""").replace('\n', ''),
                    user_scopes, allowed_scopes)
        raise OAuthScopeProblem(
            description='Provided token doesn\'t have the required scope',
            required_scopes=allowed_scopes,
            token_scopes=user_scopes
        )
    logger.info("... Token authenticated.")


def verify_oauth_local(token_info_func, allowed_scopes, function):
    """
    Decorator to verify oauth locally

    :param token_info_func: Function to get information about the token
    :type token_info_func: Function
    :param allowed_scopes: Set with scopes that are allowed to access the endpoint
    :type allowed_scopes: set
    :type function: types.FunctionType
    :rtype: types.FunctionType
    """

    @functools.wraps(function)
    def wrapper(request):
        logger.debug("%s Oauth local verification...", request.url)

        token = get_authorization_token(request)
        token_info = token_info_func(token)
        if token_info is None:
            raise OAuthResponseProblem(
                description='Provided oauth token is not valid',
                token_response=token_info
            )
        validate_token_info(token_info, allowed_scopes)
        request.context['user'] = token_info.get('uid')
        request.context['token_info'] = token_info
        return function(request)
    return wrapper


def verify_oauth_remote(token_info_url, allowed_scopes, function):
    """
    Decorator to verify oauth remotely using HTTP

    :param token_info_url: Url to get information about the token
    :type token_info_url: str
    :param allowed_scopes: Set with scopes that are allowed to access the endpoint
    :type allowed_scopes: set
    :type function: types.FunctionType
    :rtype: types.FunctionType
    """

    @functools.wraps(function)
    def wrapper(request):
        logger.debug("%s Oauth remote verification...", request.url)
        token = get_authorization_token(request)
        logger.debug("... Getting token from %s", token_info_url)
        token_request = session.get(token_info_url, headers={'Authorization': 'Bearer {}'.format(token)}, timeout=5)
        logger.debug("... Token info (%d): %s", token_request.status_code, token_request.text)
        if not token_request.ok:
            raise OAuthResponseProblem(
                description='Provided oauth token is not valid',
                token_response=token_request
            )

        token_info = token_request.json()  # type: dict
        validate_token_info(token_info, allowed_scopes)
        request.context['user'] = token_info.get('uid')
        request.context['token_info'] = token_info
        return function(request)
    return wrapper
