"""
This module defines an aiohttp-specific SecurityHandlerFactory.
"""

import logging

import aiohttp

from .async_security_handler_factory import AbstractAsyncSecurityHandlerFactory

logger = logging.getLogger("especifico.api.security")


class AioHttpSecurityHandlerFactory(AbstractAsyncSecurityHandlerFactory):
    def __init__(self, pass_context_arg_name):
        super().__init__(pass_context_arg_name=pass_context_arg_name)
        self.client_session = None

    def get_token_info_remote(self, token_info_url):
        """
        Return a function which will call `token_info_url` to retrieve token info.

        Returned function must accept oauth token in parameter.
        It must return a token_info dict in case of success, None otherwise.

        :param token_info_url: Url to get information about the token
        :type token_info_url: str
        :rtype: types.FunctionType
        """

        async def wrapper(token):
            if not self.client_session:
                # Must be created in a coroutine
                self.client_session = aiohttp.ClientSession()
            headers = {"Authorization": f"Bearer {token}"}
            token_request = await self.client_session.get(
                token_info_url, headers=headers, timeout=5,
            )
            if token_request.status != 200:
                return None
            return token_request.json()

        return wrapper
