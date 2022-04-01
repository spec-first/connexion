"""
This module defines an abstract asynchronous SecurityHandlerFactory which supports the creation of
asynchronous security handlers for coroutine operations.
"""

import abc
import asyncio
import functools
import logging

from .security_handler_factory import AbstractSecurityHandlerFactory
from ..exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem

logger = logging.getLogger("especifico.api.security")


class AbstractAsyncSecurityHandlerFactory(AbstractSecurityHandlerFactory):
    def _generic_check(self, func, exception_msg):
        (
            need_to_add_context,
            need_to_add_required_scopes,
        ) = self._need_to_add_context_or_scopes(func)

        async def wrapper(request, *args, required_scopes=None):
            kwargs = {}
            if need_to_add_context:
                kwargs[self.pass_context_arg_name] = request.context
            if need_to_add_required_scopes:
                kwargs[self.required_scopes_kw] = required_scopes
            token_info = func(*args, **kwargs)
            while asyncio.iscoroutine(token_info):
                token_info = await token_info
            if token_info is self.no_value:
                return self.no_value
            if token_info is None:
                raise OAuthResponseProblem(description=exception_msg, token_response=None)
            return token_info

        return wrapper

    def check_oauth_func(self, token_info_func, scope_validate_func):
        get_token_info = self._generic_check(token_info_func, "Provided token is not valid")
        need_to_add_context, _ = self._need_to_add_context_or_scopes(scope_validate_func)

        async def wrapper(request, token, required_scopes):
            token_info = await get_token_info(request, token, required_scopes=required_scopes)

            # Fallback to 'scopes' for backward compatibility
            token_scopes = token_info.get("scope", token_info.get("scopes", ""))

            kwargs = {}
            if need_to_add_context:
                kwargs[self.pass_context_arg_name] = request.context
            validation = scope_validate_func(required_scopes, token_scopes, **kwargs)
            while asyncio.iscoroutine(validation):
                validation = await validation
            if not validation:
                raise OAuthScopeProblem(
                    description="Provided token doesn't have the required scope",
                    required_scopes=required_scopes,
                    token_scopes=token_scopes,
                )

            return token_info

        return wrapper

    @classmethod
    def verify_security(cls, auth_funcs, function):
        @functools.wraps(function)
        async def wrapper(request):
            token_info = cls.no_value
            errors = []
            for func in auth_funcs:
                try:
                    token_info = func(request)
                    while asyncio.iscoroutine(token_info):
                        token_info = await token_info
                    if token_info is not cls.no_value:
                        break
                except Exception as err:
                    errors.append(err)

            if token_info is cls.no_value:
                if errors != []:
                    cls._raise_most_specific(errors)
                else:
                    logger.info("... No auth provided. Aborting with 401.")
                    raise OAuthProblem(description="No authorization token provided")

            # Fallback to 'uid' for backward compatibility
            request.context["user"] = token_info.get("sub", token_info.get("uid"))
            request.context["token_info"] = token_info
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
