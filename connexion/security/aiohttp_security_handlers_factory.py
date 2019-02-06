import asyncio
import aiohttp
import functools
import logging

from ..exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem
from .security_handler_factory import SecurityHandlerFactory

logger = logging.getLogger('connexion.api.security')


class AioHttpSecurityHandlerFactory(SecurityHandlerFactory):
    def __init__(self, pass_context_arg_name):
        SecurityHandlerFactory.__init__(self, pass_context_arg_name)
        self.client_session = None

    def _generic_check(self, func, exception_msg):
        need_to_add_context, need_to_add_required_scopes = self._need_to_add_context_or_scopes(func)

        @asyncio.coroutine
        def wrapper(request, *args, required_scopes=None):
            kwargs = {}
            if need_to_add_context:
                kwargs[self.pass_context_arg_name] = request.context
            if need_to_add_required_scopes:
                kwargs['required_scopes'] = required_scopes
            token_info = func(*args, **kwargs)
            while asyncio.iscoroutine(token_info):
                token_info = yield from token_info
            if token_info is self.no_value:
                return self.no_value
            if token_info is None:
                raise OAuthResponseProblem(description=exception_msg, token_response=None)
            return token_info

        return wrapper

    def check_oauth_func(self, token_info_func, scope_validate_func):
        get_token_info = self._generic_check(token_info_func, 'Provided token is not valid')
        need_to_add_context, _ = self._need_to_add_context_or_scopes(scope_validate_func)

        @asyncio.coroutine
        def wrapper(request, token, required_scopes):
            token_info = yield from get_token_info(request, token, required_scopes=required_scopes)

            # Fallback to 'scopes' for backward compatibility
            token_scopes = token_info.get('scope', token_info.get('scopes', ''))

            kwargs = {}
            if need_to_add_context:
                kwargs[self.pass_context_arg_name] = request.context
            validation = scope_validate_func(required_scopes, token_scopes, **kwargs)
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
