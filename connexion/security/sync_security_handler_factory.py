"""
This module defines a Flask-specific SecurityHandlerFactory.
"""

import functools
import logging

import requests

from ..exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem
from .security_handler_factory import AbstractSecurityHandlerFactory

logger = logging.getLogger('connexion.api.security')

# use connection pool for OAuth tokeninfo
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)


class SyncSecurityHandlerFactory(AbstractSecurityHandlerFactory):

    def _generic_check(self, func, exception_msg):
        need_to_add_context, need_to_add_required_scopes = self._need_to_add_context_or_scopes(func)

        def wrapper(request, *args, required_scopes=None):
            kwargs = {}
            if need_to_add_context:
                kwargs[self.pass_context_arg_name] = request.context
            if need_to_add_required_scopes:
                kwargs[self.required_scopes_kw] = required_scopes
            token_info = func(*args, **kwargs)
            if token_info is self.no_value:
                return self.no_value
            if token_info is None:
                raise OAuthResponseProblem(description=exception_msg, token_response=None)
            return token_info

        return wrapper

    def check_oauth_func(self, token_info_func, scope_validate_func):
        get_token_info = self._generic_check(token_info_func, 'Provided token is not valid')
        need_to_add_context, _ = self._need_to_add_context_or_scopes(scope_validate_func)

        def wrapper(request, token, required_scopes):
            token_info = get_token_info(request, token, required_scopes=required_scopes)

            # Fallback to 'scopes' for backward compatibility
            token_scopes = token_info.get('scope', token_info.get('scopes', ''))

            kwargs = {}
            if need_to_add_context:
                kwargs[self.pass_context_arg_name] = request.context
            validation = scope_validate_func(required_scopes, token_scopes, **kwargs)
            if not validation:
                raise OAuthScopeProblem(
                    description='Provided token doesn\'t have the required scope',
                    required_scopes=required_scopes,
                    token_scopes=token_scopes
                )

            return token_info
        return wrapper

    @classmethod
    def verify_security(cls, auth_funcs, required_scopes, function):

        @functools.wraps(function)
        def wrapper(request):
            token_info = cls.no_value
            for func in auth_funcs:
                token_info = func(request, required_scopes)
                if token_info is not cls.no_value:
                    break

            if token_info is cls.no_value:
                logger.info("... No auth provided. Aborting with 401.")
                raise OAuthProblem(description='No authorization token provided')

            # Fallback to 'uid' for backward compatibility
            request.context['user'] = token_info.get('sub', token_info.get('uid'))
            request.context['token_info'] = token_info
            return function(request)

        return wrapper

    def get_token_info_remote(self, token_info_url):
        """
        Return a function which will call `token_info_url` to retrieve token info.

        Returned function must accept oauth token in parameter.
        It must return a token_info dict in case of success, None otherwise.

        :param token_info_url: Url to get information about the token
        :type token_info_url: str
        :rtype: types.FunctionType
        """
        def wrapper(token):
            """
            Retrieve oauth token_info remotely using HTTP
            :param token: oauth token from authorization header
            :type token: str
            :rtype: dict
            """
            headers = {'Authorization': f'Bearer {token}'}
            token_request = session.get(token_info_url, headers=headers, timeout=5)
            if not token_request.ok:
                return None
            return token_request.json()
        return wrapper
