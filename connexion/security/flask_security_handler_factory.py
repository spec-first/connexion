import requests

from .security_handler_factory import SecurityHandlerFactory

# use connection pool for OAuth tokeninfo
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)


class FlaskSecurityHandlerFactory(SecurityHandlerFactory):
    def __init__(self, pass_context_arg_name):
        SecurityHandlerFactory.__init__(self, pass_context_arg_name)

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
            headers = {'Authorization': 'Bearer {}'.format(token)}
            token_request = session.get(token_info_url, headers=headers, timeout=5)
            if not token_request.ok:
                return None
            return token_request.json()
        return wrapper
