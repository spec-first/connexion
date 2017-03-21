# Authentication and authorization related decorators
import functools
import logging
import os
import textwrap

import requests
from flask import request

from ..exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem

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


def get_client_ip(request, trusted_ips):
    if request.headers.get("X-Forwarded-For") and request.remote_addr in trusted_ips:
        return request.headers.get("X-Forwarded-For")
    return request.remote_addr


def nice_scopes(scopes):
    if not scopes:
        return "None"
    return ','.join(scopes)


def security_passthrough(function):
    """
    :type function: types.FunctionType
    :rtype: types.FunctionTyperequest.headers
    """
    return function


def verify_oauth(token_info_url, allowed_scopes, trusted_ips, function):
    """
    Decorator to verify oauth

    :param token_info_url: Url to get information about the token
    :type token_info_url: str
    :param allowed_scopes: Set with scopes that are allowed to access the endpoint
    :type allowed_scopes: set
    :type function: types.FunctionType
    :rtype: types.FunctionType
    :param trusted_ips: A list of trusted IPs. If request.remote_addr is in this list (i.e. it's a proxy we control)
    then we'll also trust the X-Forwarded-For HTTP header.
    :type trusted_ips: list
    """
    trusted_ips = trusted_ips or []

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug("%s Oauth verification...", request.url)
        authorization = request.headers.get('Authorization')  # type: str
        if not authorization:
            logger.info("... No auth provided. Aborting with 401.")
            raise OAuthProblem(description='No authorization token provided')
        else:
            try:
                _, token = authorization.split()  # type: str, str
            except ValueError:
                raise OAuthProblem(description='Invalid authorization header')
            logger.debug("... Getting token from %s", token_info_url)
            token_request = session.get(token_info_url, params={'access_token': token}, timeout=5)
            client_ip = get_client_ip(request, trusted_ips)
            logger.debug("... Token info (%d): %s for client IP '%s'",
                         token_request.status_code,
                         token_request.text,
                         client_ip)
            if not token_request.ok:
                raise OAuthResponseProblem(
                    description='Provided oauth token is not valid',
                    token_response=token_request
                )
            token_info = token_request.json()  # type: dict
            user_scopes = set(token_info['scope'])
            logger.debug("... Scopes required: %s", nice_scopes(allowed_scopes))
            logger.debug("... User scopes: %s", nice_scopes(user_scopes))
            if not allowed_scopes <= user_scopes:
                logger.info(textwrap.dedent("""
                            ... User scopes (%s) do not match the scopes necessary to call endpoint (%s).
                             Aborting with 403 for client IP '%s'""").replace('\n', ''),
                            nice_scopes(user_scopes), nice_scopes(allowed_scopes), client_ip)
                raise OAuthScopeProblem(
                    description='Provided token doesn\'t have the required scope',
                    required_scopes=allowed_scopes,
                    token_scopes=user_scopes
                )
            logger.info("... Token authenticated.")
            request.user = token_info.get('uid')
            request.token_info = token_info
        return function(*args, **kwargs)

    return wrapper
