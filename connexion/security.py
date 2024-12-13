"""
This module defines a SecurityHandlerFactory which supports the creation of
SecurityHandler instances for different security schemes.

It also exposes a `SECURITY_HANDLERS` dictionary which maps security scheme
types to SecurityHandler classes. This dictionary can be used to register
custom SecurityHandler classes for custom security schemes, or to overwrite
existing SecurityHandler classes.
This can be done by supplying a value for `security_map` argument of the
SecurityHandlerFactory.

Swagger 2.0 lets you define the following authentication types for an API:

- Basic authentication
- API key (as a header or a query string parameter)
- OAuth 2 common flows (authorization code, implicit, resource owner password credentials, client credentials)


Changes from OpenAPI 2.0 to OpenAPI 3.0
If you used OpenAPI 2.0 before, here is a summary of changes to help you get started with OpenAPI 3.0:
- securityDefinitions were renamed to securitySchemes and moved inside components.
- type: basic was replaced with type: http and scheme: basic.
- The new type: http is an umbrella type for all HTTP security schemes, including Basic, Bearer and other,
and the scheme keyword indicates the scheme type.
- API keys can now be sent in: cookie.
- Added support for OpenID Connect Discovery (type: openIdConnect).
- OAuth 2 security schemes can now define multiple flows.
- OAuth 2 flows were renamed to match the OAuth 2 Specification: accessCode is now authorizationCode,
and application is now clientCredentials.


OpenAPI uses the term security scheme for authentication and authorization schemes.
OpenAPI 3.0 lets you describe APIs protected using the following security schemes:

- HTTP authentication schemes (they use the Authorization header):
    - Basic
    - Bearer
    - other HTTP schemes as defined by RFC 7235 and HTTP Authentication Scheme Registry
- API keys in headers, query string or cookies
    - Cookie authentication
- OAuth 2
- OpenID Connect Discovery

"""

import asyncio
import base64
import http.cookies
import logging
import os
import typing as t

import httpx

from connexion.decorators.parameter import inspect_function_arguments
from connexion.exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem
from connexion.lifecycle import ConnexionRequest
from connexion.utils import get_function_from_name

logger = logging.getLogger(__name__)


NO_VALUE = object()
"""Sentinel value to indicate that no security credentials were found."""


class AbstractSecurityHandler:

    required_scopes_kw = "required_scopes"
    request_kw = "request"
    client = None
    security_definition_key: str
    """The key which contains the value for the function name to resolve."""
    environ_key: str
    """The name of the environment variable that can be used alternatively for the function name."""

    def get_fn(self, security_scheme, required_scopes):
        """Returns the handler function"""
        security_func = self._resolve_func(security_scheme)
        if not security_func:
            logger.warning("... %s missing", self.security_definition_key)
            return None

        return self._get_verify_func(security_func)

    @classmethod
    def _get_function(
        cls,
        security_definition: dict,
        security_definition_key: str,
        environ_key: str,
        default: t.Optional[t.Callable] = None,
    ):
        """
        Return function by getting its name from security_definition or environment variable

        :param security_definition: Security Definition (scheme) from the spec.
        :param security_definition_key: The key which contains the value for the function name to resolve.
        :param environ_key: The name of the environment variable that can be used alternatively for the function name.
        :param default: The default to use in case the function cannot be found based on the security_definition_key or the environ_key
        """
        func_name = security_definition.get(security_definition_key) or os.environ.get(
            environ_key
        )
        if func_name:
            return get_function_from_name(func_name)
        return default

    def _generic_check(self, func, exception_msg):
        async def wrapper(request, *args, required_scopes=None):
            kwargs = {}
            if self._accepts_kwarg(func, self.required_scopes_kw):
                kwargs[self.required_scopes_kw] = required_scopes
            if self._accepts_kwarg(func, self.request_kw):
                kwargs[self.request_kw] = request
            token_info = func(*args, **kwargs)
            while asyncio.iscoroutine(token_info):
                token_info = await token_info
            if token_info is NO_VALUE:
                return NO_VALUE
            if token_info is None:
                raise OAuthResponseProblem(detail=exception_msg)
            return token_info

        return wrapper

    @staticmethod
    def get_auth_header_value(request):
        """
        Return Authorization type and value if any.
        If not Authorization, return (None, None)
        Raise OAuthProblem for invalid Authorization header
        """
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None, None

        try:
            auth_type, value = authorization.split(maxsplit=1)
        except ValueError:
            raise OAuthProblem(detail="Invalid authorization header")
        return auth_type.lower(), value

    @staticmethod
    def _accepts_kwarg(func: t.Callable, keyword: str) -> bool:
        """Check if the function accepts the provided keyword argument."""
        arguments, has_kwargs = inspect_function_arguments(func)
        return has_kwargs or keyword in arguments

    def _resolve_func(self, security_scheme):
        """
        Get the user function object based on the security scheme or the environment variable.

        :param security_scheme: Security Definition (scheme) from the spec.
        """
        return self._get_function(
            security_scheme, self.security_definition_key, self.environ_key
        )

    def _get_verify_func(self, function):
        """
        Wraps the user security function in a function that checks the request for the correct
        security credentials and calls the user function with the correct arguments.
        """
        return self._generic_check(function, "Provided authorization is not valid")


class BasicSecurityHandler(AbstractSecurityHandler):
    """
    Security Handler for
    - `type: basic` (Swagger 2), and
    - `type: http` and `scheme: basic` (OpenAPI 3)
    """

    security_definition_key = "x-basicInfoFunc"
    environ_key = "BASICINFO_FUNC"

    def _get_verify_func(self, basic_info_func):
        check_basic_info_func = self.check_basic_auth(basic_info_func)

        def wrapper(request):
            auth_type, user_pass = self.get_auth_header_value(request)
            if auth_type != "basic":
                return NO_VALUE

            try:
                username, password = (
                    base64.b64decode(user_pass).decode("latin1").split(":", 1)
                )
            except Exception:
                raise OAuthProblem(detail="Invalid authorization header")

            return check_basic_info_func(request, username, password)

        return wrapper

    def check_basic_auth(self, basic_info_func):
        return self._generic_check(
            basic_info_func, "Provided authorization is not valid"
        )


class BearerSecurityHandler(AbstractSecurityHandler):
    """
    Security Handler for HTTP Bearer authentication.
    """

    security_definition_key = "x-bearerInfoFunc"
    environ_key = "BEARERINFO_FUNC"

    def check_bearer_token(self, token_info_func):
        return self._generic_check(token_info_func, "Provided token is not valid")

    def _get_verify_func(self, token_info_func):
        """
        :param token_info_func: types.FunctionType
        :rtype: types.FunctionType
        """
        check_bearer_func = self.check_bearer_token(token_info_func)

        def wrapper(request):
            auth_type, token = self.get_auth_header_value(request)
            if auth_type != "bearer":
                return NO_VALUE
            return check_bearer_func(request, token)

        return wrapper


class ApiKeySecurityHandler(AbstractSecurityHandler):
    """
    Security Handler for API Keys.
    """

    security_definition_key = "x-apikeyInfoFunc"
    environ_key = "APIKEYINFO_FUNC"

    def get_fn(self, security_scheme, required_scopes):
        apikey_info_func = self._resolve_func(security_scheme)
        if not apikey_info_func:
            logger.warning("... %s missing", self.security_definition_key)
            return None

        return self._get_verify_func(
            apikey_info_func,
            security_scheme["in"],
            security_scheme["name"],
            required_scopes,
        )

    def _get_verify_func(self, api_key_info_func, loc, name, required_scopes):
        check_api_key_func = self.check_api_key(api_key_info_func)

        def wrapper(request: ConnexionRequest):
            if loc == "query":
                api_key = request.query_params.get(name)
            elif loc == "header":
                api_key = request.headers.get(name)
            elif loc == "cookie":
                cookie_list = request.headers.get("Cookie")
                api_key = self.get_cookie_value(cookie_list, name)
            else:
                return NO_VALUE

            if api_key is None:
                return NO_VALUE

            return check_api_key_func(request, api_key, required_scopes=required_scopes)

        return wrapper

    def check_api_key(self, api_key_info_func):
        return self._generic_check(api_key_info_func, "Provided apikey is not valid")

    @staticmethod
    def get_cookie_value(cookies, name):
        """
        Returns cookie value by its name. `None` if no such value.

        :param cookies: str: cookies raw data
        :param name: str: cookies key
        """
        cookie_parser = http.cookies.SimpleCookie()
        cookie_parser.load(str(cookies))
        try:
            return cookie_parser[name].value
        except KeyError:
            return None


class OAuthSecurityHandler(AbstractSecurityHandler):
    """
    Security Handler for the OAuth security scheme.
    """

    def get_fn(self, security_scheme, required_scopes):
        token_info_func = self.get_tokeninfo_func(security_scheme)
        scope_validate_func = self.get_scope_validate_func(security_scheme)
        if not token_info_func:
            logger.warning("... x-tokenInfoFunc missing")
            return None

        return self._get_verify_func(
            token_info_func, scope_validate_func, required_scopes
        )

    def get_tokeninfo_func(self, security_definition: dict) -> t.Optional[t.Callable]:
        """
        Gets the function for retrieving the token info.
        It is possible to specify a function or a URL. The function variant is
        preferred. If it is not found, the URL variant is used with the
        `get_token_info_remote` function.

        >>> get_tokeninfo_func({'x-tokenInfoFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        token_info_func = self._get_function(
            security_definition, "x-tokenInfoFunc", "TOKENINFO_FUNC"
        )
        if token_info_func:
            return token_info_func

        token_info_url = security_definition.get("x-tokenInfoUrl") or os.environ.get(
            "TOKENINFO_URL"
        )
        if token_info_url:
            return self.get_token_info_remote(token_info_url)

        return None

    @classmethod
    def get_scope_validate_func(cls, security_definition):
        """
        Gets the function for validating the token scopes.
        If it is not found, the default `validate_scope` function is used.

        >>> get_scope_validate_func({'x-scopeValidateFunc': 'foo.bar'})
        '<function foo.bar>'
        """
        return cls._get_function(
            security_definition,
            "x-scopeValidateFunc",
            "SCOPEVALIDATE_FUNC",
            cls.validate_scope,
        )

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
            logger.info(
                "... Token scopes (%s) do not match the scopes necessary to call endpoint (%s)."
                " Aborting with 403.",
                token_scopes,
                required_scopes,
            )
            return False
        return True

    def get_token_info_remote(self, token_info_url: str) -> t.Callable:
        """
        Return a function which will call `token_info_url` to retrieve token info.

        Returned function must accept oauth token in parameter.
        It must return a token_info dict in case of success, None otherwise.

        :param token_info_url: URL to get information about the token
        """

        async def wrapper(token):
            if self.client is None:
                self.client = httpx.AsyncClient()
            headers = {"Authorization": f"Bearer {token}"}
            token_request = await self.client.get(
                token_info_url, headers=headers, timeout=5
            )
            if token_request.status_code != 200:
                return
            return token_request.json()

        return wrapper

    def _get_verify_func(self, token_info_func, scope_validate_func, required_scopes):
        check_oauth_func = self.check_oauth_func(token_info_func, scope_validate_func)

        def wrapper(request):
            auth_type, token = self.get_auth_header_value(request)
            if auth_type != "bearer":
                return NO_VALUE

            return check_oauth_func(request, token, required_scopes=required_scopes)

        return wrapper

    def check_oauth_func(self, token_info_func, scope_validate_func):
        get_token_info = self._generic_check(
            token_info_func, "Provided token is not valid"
        )

        async def wrapper(request, token, required_scopes):
            token_info = await get_token_info(
                request, token, required_scopes=required_scopes
            )

            # Fallback to 'scopes' for backward compatibility
            token_scopes = token_info.get("scope", token_info.get("scopes", ""))

            validation = scope_validate_func(required_scopes, token_scopes)
            while asyncio.iscoroutine(validation):
                validation = await validation
            if not validation:
                raise OAuthScopeProblem(
                    required_scopes=required_scopes,
                    token_scopes=token_scopes,
                )

            return token_info

        return wrapper


SECURITY_HANDLERS = {
    # Swagger 2: `type: basic`
    # OpenAPI 3: `type: http` and `scheme: basic`
    "basic": BasicSecurityHandler,
    # Swagger 2 and OpenAPI 3
    "apiKey": ApiKeySecurityHandler,
    "oauth2": OAuthSecurityHandler,
    # OpenAPI 3: http schemes
    "bearer": BearerSecurityHandler,
}


class SecurityHandlerFactory:
    """
    A factory class for parsing security schemes and returning the appropriate
    security handler.

    By default, it will use the built-in security handlers specified in the
    SECURITY_HANDLERS dict, but you can also pass in your own security handlers
    to override the built-in ones.
    """

    def __init__(
        self,
        security_handlers: t.Optional[dict] = None,
    ) -> None:
        self.security_handlers = SECURITY_HANDLERS.copy()
        if security_handlers is not None:
            self.security_handlers.update(security_handlers)

    def parse_security_scheme(
        self,
        security_scheme: dict,
        required_scopes: t.List[str],
    ) -> t.Optional[t.Callable]:
        """Parses the security scheme and returns the function for verifying it.

        :param security_scheme: The security scheme from the spec.
        :param required_scopes: List of scopes for this security scheme.
        """
        security_type = security_scheme["type"]
        if security_type in ("basic", "oauth2"):
            security_handler = self.security_handlers[security_type]
            return security_handler().get_fn(security_scheme, required_scopes)

        # OpenAPI 3.0.0
        elif security_type == "http":
            scheme = security_scheme["scheme"].lower()
            if scheme in self.security_handlers:
                security_handler = self.security_handlers[scheme]
                return security_handler().get_fn(security_scheme, required_scopes)
            else:
                logger.warning("... Unsupported http authorization scheme %s", scheme)
                return None

        elif security_type == "apiKey":
            scheme = security_scheme.get("x-authentication-scheme", "").lower()
            if scheme == "bearer":
                return BearerSecurityHandler().get_fn(security_scheme, required_scopes)
            else:
                security_handler = self.security_handlers["apiKey"]
                return security_handler().get_fn(security_scheme, required_scopes)

        elif security_type == "openIdConnect":
            if security_type in self.security_handlers:
                security_handler = self.security_handlers[security_type]
                return security_handler().get_fn(security_scheme, required_scopes)
            logger.warning("... No default implementation for openIdConnect")
            return None

        # Custom security scheme handler
        elif (
            "scheme" in security_scheme
            and (scheme := security_scheme["scheme"].lower()) in self.security_handlers
        ):
            security_handler = self.security_handlers[scheme]
            return security_handler().get_fn(security_scheme, required_scopes)

        # Custom security type handler
        elif security_type in self.security_handlers:
            security_handler = self.security_handlers[security_type]
            return security_handler().get_fn(security_scheme, required_scopes)

        else:
            logger.warning(
                "... Unsupported security scheme type %s",
                security_type,
            )
            return None

    @staticmethod
    async def security_passthrough(request):
        """Used when no security is required for the operation.

        Equivalent OpenAPI snippet:

        .. code-block:: yaml

            /helloworld
              get:
                security: []   # No security
                ...
        """
        return request

    @staticmethod
    def verify_none(request):
        """Used for optional security.

        Equivalent OpenAPI snippet:

        .. code-block:: yaml

            security:
              - {}  # <--
              - myapikey: []
        """
        return {}

    def verify_multiple_schemes(self, schemes):
        """
        Verifies multiple authentication schemes in AND fashion.
        If any scheme fails, the entire authentication fails.

        :param schemes: mapping scheme_name to auth function
        :type schemes: dict
        :rtype: types.FunctionType
        """

        async def wrapper(request):
            token_info = {}
            for scheme_name, func in schemes.items():
                result = func(request)
                while asyncio.iscoroutine(result):
                    result = await result
                if result is NO_VALUE:
                    return NO_VALUE
                token_info[scheme_name] = result

            return token_info

        return wrapper

    @classmethod
    def verify_security(cls, auth_funcs):
        async def verify_fn(request):
            token_info = NO_VALUE
            errors = []
            for func in auth_funcs:
                try:
                    token_info = func(request)
                    while asyncio.iscoroutine(token_info):
                        token_info = await token_info
                    if token_info is not NO_VALUE:
                        break
                except Exception as err:
                    errors.append(err)

            else:
                if errors != []:
                    cls._raise_most_specific(errors)
                else:
                    logger.info("... No auth provided. Aborting with 401.")
                    raise OAuthProblem(detail="No authorization token provided")

            request.context.update(
                {
                    # Fallback to 'uid' for backward compatibility
                    "user": token_info.get("sub", token_info.get("uid")),
                    "token_info": token_info,
                }
            )

        return verify_fn

    @staticmethod
    def _raise_most_specific(exceptions: t.List[Exception]) -> None:
        """Raises the most specific error from a list of exceptions by status code.

        The status codes are expected to be either in the `code`
        or in the `status` attribute of the exceptions.

        The order is as follows:
            - 403: valid credentials but not enough privileges
            - 401: no or invalid credentials
            - for other status codes, the smallest one is selected

        :param errors: List of exceptions.
        :type errors: t.List[Exception]
        """
        if not exceptions:
            return
        # We only use status code attributes from exceptions
        # We use 600 as default because 599 is highest valid status code
        status_to_exc = {
            getattr(exc, "status_code", getattr(exc, "status", 600)): exc
            for exc in exceptions
        }
        if 403 in status_to_exc:
            raise status_to_exc[403]
        elif 401 in status_to_exc:
            raise status_to_exc[401]
        else:
            lowest_status_code = min(status_to_exc)
            raise status_to_exc[lowest_status_code]
