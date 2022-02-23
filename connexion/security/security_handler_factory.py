"""
This module defines an abstract SecurityHandlerFactory which supports the creation of security
handlers for operations.
"""

import abc
import base64
import functools
import http.cookies
import logging
import os
import textwrap
import typing as t

from ..decorators.parameter import inspect_function_arguments
from ..exceptions import (ConnexionException, OAuthProblem,
                          OAuthResponseProblem, OAuthScopeProblem)
from ..utils import get_function_from_name

logger = logging.getLogger('connexion.api.security')


class AbstractSecurityHandlerFactory(abc.ABC):
    """
    get_*_func -> _get_function -> get_function_from_name (name=security function defined in spec)
        (if url defined instead of a function -> get_token_info_remote)

    std security functions: security_{passthrough,deny}

    verify_* -> returns a security wrapper around the security function
        check_* -> returns a function tasked with doing auth for use inside the verify wrapper
            check helpers (used outside wrappers): _need_to_add_context_or_scopes
            the security function

        verify helpers (used inside wrappers): get_auth_header_value, get_cookie_value
    """
    no_value = object()
    required_scopes_kw = 'required_scopes'

    def __init__(self, pass_context_arg_name):
        self.pass_context_arg_name = pass_context_arg_name

    @staticmethod
    def _get_function(security_definition, security_definition_key, environ_key, default=None):
        """
        Return function by getting its name from security_definition or environment variable
        """
        func = security_definition.get(security_definition_key) or os.environ.get(environ_key)
        if func:
            return get_function_from_name(func)
        return default

    def get_tokeninfo_func(self, security_definition: dict) -> t.Optional[t.Callable]:
        """
        :type security_definition: dict

        >>> get_tokeninfo_url({'x-tokenInfoFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        token_info_func = self._get_function(security_definition, "x-tokenInfoFunc", 'TOKENINFO_FUNC')
        if token_info_func:
            return token_info_func

        token_info_url = (security_definition.get('x-tokenInfoUrl') or
                          os.environ.get('TOKENINFO_URL'))
        if token_info_url:
            return self.get_token_info_remote(token_info_url)

        return None

    @classmethod
    def get_scope_validate_func(cls, security_definition):
        """
        :type security_definition: dict
        :rtype: function

        >>> get_scope_validate_func({'x-scopeValidateFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        return cls._get_function(security_definition, "x-scopeValidateFunc", 'SCOPEVALIDATE_FUNC', cls.validate_scope)

    @classmethod
    def get_basicinfo_func(cls, security_definition):
        """
        :type security_definition: dict
        :rtype: function

        >>> get_basicinfo_func({'x-basicInfoFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        return cls._get_function(security_definition, "x-basicInfoFunc", 'BASICINFO_FUNC')

    @classmethod
    def get_apikeyinfo_func(cls, security_definition):
        """
        :type security_definition: dict
        :rtype: function

        >>> get_apikeyinfo_func({'x-apikeyInfoFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        return cls._get_function(security_definition, "x-apikeyInfoFunc", 'APIKEYINFO_FUNC')

    @classmethod
    def get_bearerinfo_func(cls, security_definition):
        """
        :type security_definition: dict
        :rtype: function

        >>> get_bearerinfo_func({'x-bearerInfoFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        return cls._get_function(security_definition, "x-bearerInfoFunc", 'BEARERINFO_FUNC')

    @staticmethod
    def security_passthrough(function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        return function

    @staticmethod
    def security_deny(function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        def deny(*args, **kwargs):
            raise ConnexionException("Error in security definitions")

        return deny

    @staticmethod
    def validate_scope(required_scopes, token_scopes):
        """
        :param required_scopes: Scopes required to access operation
        :param token_scopes: Scopes granted by authorization server
        :rtype: bool
        """
        required_scopes = set(required_scopes)
        if isinstance(token_scopes, list):
            token_scopes = set(token_scopes)
        else:
            token_scopes = set(token_scopes.split())
        logger.debug("... Scopes required: %s", required_scopes)
        logger.debug("... Token scopes: %s", token_scopes)
        if not required_scopes <= token_scopes:
            logger.info(textwrap.dedent("""
                        ... Token scopes (%s) do not match the scopes necessary to call endpoint (%s).
                         Aborting with 403.""").replace('\n', ''),
                        token_scopes, required_scopes)
            return False
        return True

    @staticmethod
    def get_auth_header_value(request):
        """
        Called inside security wrapper functions

        Return Authorization type and value if any.
        If not Authorization, return (None, None)
        Raise OAuthProblem for invalid Authorization header
        """
        authorization = request.headers.get('Authorization')
        if not authorization:
            return None, None

        try:
            auth_type, value = authorization.split(None, 1)
        except ValueError:
            raise OAuthProblem(description='Invalid authorization header')
        return auth_type.lower(), value

    def verify_oauth(self, token_info_func, scope_validate_func):
        check_oauth_func = self.check_oauth_func(token_info_func, scope_validate_func)

        def wrapper(request, required_scopes):
            auth_type, token = self.get_auth_header_value(request)
            if auth_type != 'bearer':
                return self.no_value

            return check_oauth_func(request, token, required_scopes=required_scopes)

        return wrapper

    def verify_basic(self, basic_info_func):
        check_basic_info_func = self.check_basic_auth(basic_info_func)

        def wrapper(request, required_scopes):
            auth_type, user_pass = self.get_auth_header_value(request)
            if auth_type != 'basic':
                return self.no_value

            try:
                username, password = base64.b64decode(user_pass).decode('latin1').split(':', 1)
            except Exception:
                raise OAuthProblem(description='Invalid authorization header')

            return check_basic_info_func(request, username, password, required_scopes=required_scopes)

        return wrapper

    @staticmethod
    def get_cookie_value(cookies, name):
        '''
        Called inside security wrapper functions

        Returns cookie value by its name. None if no such value.
        :param cookies: str: cookies raw data
        :param name: str: cookies key
        '''
        cookie_parser = http.cookies.SimpleCookie()
        cookie_parser.load(str(cookies))
        try:
            return cookie_parser[name].value
        except KeyError:
            return None

    def verify_api_key(self, api_key_info_func, loc, name):
        check_api_key_func = self.check_api_key(api_key_info_func)

        def wrapper(request, required_scopes):

            def _immutable_pop(_dict, key):
                """
                Pops the key from an immutable dict and returns the value that was popped,
                and a new immutable dict without the popped key.
                """
                cls = type(_dict)
                try:
                    _dict = _dict.to_dict(flat=False)
                    return _dict.pop(key)[0], cls(_dict)
                except AttributeError:
                    _dict = dict(_dict.items())
                    return _dict.pop(key), cls(_dict)

            if loc == 'query':
                try:
                    api_key, request.query = _immutable_pop(request.query, name)
                except KeyError:
                    api_key = None
            elif loc == 'header':
                api_key = request.headers.get(name)
            elif loc == 'cookie':
                cookie_list = request.headers.get('Cookie')
                api_key = self.get_cookie_value(cookie_list, name)
            else:
                return self.no_value

            if api_key is None:
                return self.no_value

            return check_api_key_func(request, api_key, required_scopes=required_scopes)

        return wrapper

    def verify_bearer(self, token_info_func):
        """
        :param token_info_func: types.FunctionType
        :rtype: types.FunctionType
        """
        check_bearer_func = self.check_bearer_token(token_info_func)

        def wrapper(request, required_scopes):
            auth_type, token = self.get_auth_header_value(request)
            if auth_type != 'bearer':
                return self.no_value
            return check_bearer_func(request, token, required_scopes=required_scopes)

        return wrapper

    def verify_multiple_schemes(self, schemes):
        """
        Verifies multiple authentication schemes in AND fashion.
        If any scheme fails, the entire authentication fails.

        :param schemes: mapping scheme_name to auth function
        :type schemes: dict
        :rtype: types.FunctionType
        """

        def wrapper(request, required_scopes):
            token_info = {}
            for scheme_name, func in schemes.items():
                result = func(request, required_scopes)
                if result is self.no_value:
                    return self.no_value
                token_info[scheme_name] = result

            return token_info

        return wrapper

    @staticmethod
    def verify_none():
        """
        :rtype: types.FunctionType
        """

        def wrapper(request, required_scopes):
            return {}

        return wrapper

    def _need_to_add_context_or_scopes(self, func):
        arguments, has_kwargs = inspect_function_arguments(func)
        need_context = self.pass_context_arg_name and (has_kwargs or self.pass_context_arg_name in arguments)
        need_required_scopes = has_kwargs or self.required_scopes_kw in arguments
        return need_context, need_required_scopes

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

    def check_bearer_token(self, token_info_func):
        return self._generic_check(token_info_func, 'Provided token is not valid')

    def check_basic_auth(self, basic_info_func):
        return self._generic_check(basic_info_func, 'Provided authorization is not valid')

    def check_api_key(self, api_key_info_func):
        return self._generic_check(api_key_info_func, 'Provided apikey is not valid')

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

    @abc.abstractmethod
    def get_token_info_remote(self, token_info_url):
        """
        Return a function which will call `token_info_url` to retrieve token info.

        Returned function must accept oauth token in parameter.
        It must return a token_info dict in case of success, None otherwise.

        :param token_info_url: Url to get information about the token
        :type token_info_url: str
        :rtype: types.FunctionType
        """
