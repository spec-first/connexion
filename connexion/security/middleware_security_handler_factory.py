"""
"""

import logging

from .async_security_handler_factory import AbstractAsyncSecurityHandlerFactory

logger = logging.getLogger('connexion.api.security')


class MiddlewareSecurityHandlerFactory(AbstractAsyncSecurityHandlerFactory):
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
            return
        return wrapper
