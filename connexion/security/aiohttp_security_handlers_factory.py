import asyncio
import aiohttp
import functools
import logging

from ..exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem
from .security_handler_factory import SecurityHandlerFactory

logger = logging.getLogger('connexion.api.security')


class AioHttpSecurityHandlerFactory(SecurityHandlerFactory):
    def __init__(self):
        self.client_session = None

    @classmethod
    def check_bearer_token(cls, token_info_func):
        @asyncio.coroutine
        def wrapper(request, token, required_scopes):
            token_info = token_info_func(token)
            while asyncio.iscoroutine(token_info):
                token_info = yield from token_info
            if token_info is cls.no_value:
                return cls.no_value
            if token_info is None:
                raise OAuthResponseProblem(
                    description='Provided token is not valid',
                    token_response=None
                )

            return token_info
        return wrapper

    @classmethod
    def check_basic_auth(cls, basic_info_func):
        @asyncio.coroutine
        def wrapper(request, username, password, required_scopes):
            token_info = basic_info_func(username, password, required_scopes=required_scopes)
            while asyncio.iscoroutine(token_info):
                token_info = yield from token_info
            if token_info is cls.no_value:
                return cls.no_value
            if token_info is None:
                raise OAuthResponseProblem(
                    description='Provided authorization is not valid',
                    token_response=None
                )

            return token_info
        return wrapper

    @classmethod
    def check_api_key(cls, api_key_info_func):
        @asyncio.coroutine
        def wrapper(request, api_key, required_scopes):
            token_info = api_key_info_func(api_key, required_scopes=required_scopes)
            while asyncio.iscoroutine(token_info):
                token_info = yield from token_info
            if token_info is cls.no_value:
                return cls.no_value
            if token_info is None:
                raise OAuthResponseProblem(
                    description='Provided apikey is not valid',
                    token_response=None
                )
            return token_info
        return wrapper

    @classmethod
    def check_oauth_func(cls, token_info_func, scope_validate_func):
        @asyncio.coroutine
        def wrapper(request, token, required_scopes):

            token_info = token_info_func(token)
            while asyncio.iscoroutine(token_info):
                token_info = yield from token_info
            if token_info is cls.no_value:
                return cls.no_value
            if token_info is None:
                raise OAuthResponseProblem(
                    description='Provided token is not valid',
                    token_response=None
                )

            # Fallback to 'scopes' for backward compatibility
            token_scopes = token_info.get('scope', token_info.get('scopes', ''))

            validation = scope_validate_func(required_scopes, token_scopes)
            while asyncio.iscoroutine(validation):
                validation = yield from validation
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
        @asyncio.coroutine
        @functools.wraps(function)
        def wrapper(request):
            token_info = None
            for func in auth_funcs:
                token_info = func(request, required_scopes)
                while asyncio.iscoroutine(token_info):
                    token_info = yield from token_info
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
        @asyncio.coroutine
        def wrapper(token):
            if not self.client_session:
                # Must be created in a coroutine
                self.client_session = aiohttp.ClientSession()
            headers = {'Authorization': 'Bearer {}'.format(token)}
            token_request = yield from self.client_session.get(token_info_url, headers=headers, timeout=5)
            if token_request.status != 200:
                return None
            return token_request.json()
        return wrapper
