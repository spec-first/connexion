import functools
import logging

from ..decorators.decorator import (BeginOfRequestLifecycleDecorator,
                                    EndOfRequestLifecycleDecorator)
from ..decorators.security import (get_tokeninfo_func, get_tokeninfo_url,
                                   security_passthrough, verify_oauth_local,
                                   verify_oauth_remote)

logger = logging.getLogger("connexion.operations.secure")

DEFAULT_MIMETYPE = 'application/json'


class SecureOperation(object):

    def __init__(self, api, security, security_schemes):
        """
        :param security: list of security rules the application uses by default
        :type security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        """
        self._api = api
        self._security = security
        self._security_schemes = security_schemes

    @property
    def api(self):
        return self._api

    @property
    def security(self):
        return self._security

    @property
    def security_schemes(self):
        return self._security_schemes

    @property
    def security_decorator(self):
        """
        Gets the security decorator for operation

        From Swagger Specification:

        **Security Definitions Object**

        A declaration of the security schemes available to be used in the specification.

        This does not enforce the security schemes on the operations and only serves to provide the relevant details
        for each scheme.


        **Security Requirement Object**

        Lists the required security schemes to execute this operation. The object can have multiple security schemes
        declared in it which are all required (that is, there is a logical AND between the schemes).

        The name used for each property **MUST** correspond to a security scheme declared in the Security Definitions.

        :rtype: types.FunctionType
        """
        logger.debug('... Security: %s', self.security, extra=vars(self))
        if self.security:
            if len(self.security) > 1:
                logger.debug("... More than one security requirement defined. **IGNORING SECURITY REQUIREMENTS**",
                             extra=vars(self))
                return security_passthrough

            security = self.security[0]  # type: dict
            # the following line gets the first (and because of the previous condition only) scheme and scopes
            # from the operation's security requirements

            scheme_name, scopes = next(iter(security.items()))  # type: str, list
            security_definition = self.security_schemes[scheme_name]
            if security_definition['type'] == 'oauth2':
                token_info_url = get_tokeninfo_url(security_definition)
                token_info_func = get_tokeninfo_func(security_definition)
                scopes = set(scopes)  # convert scopes to set because this is needed for verify_oauth_remote

                if token_info_url and token_info_func:
                    logger.warning("... Both x-tokenInfoUrl and x-tokenInfoFunc are defined, using x-tokenInfoFunc",
                                   extra=vars(self))
                if token_info_func:
                    return functools.partial(verify_oauth_local, token_info_func, scopes)
                if token_info_url:
                    return functools.partial(verify_oauth_remote, token_info_url, scopes)
                else:
                    logger.warning("... OAuth2 token info URL missing. **IGNORING SECURITY REQUIREMENTS**",
                                   extra=vars(self))
            elif security_definition['type'] in ('apiKey', 'basic'):
                logger.debug(
                    "... Security type '%s' not natively supported by Connexion; you should handle it yourself",
                    security_definition['type'], extra=vars(self))

        # if we don't know how to handle the security or it's not defined we will usa a passthrough decorator
        return security_passthrough

    def get_mimetype(self):
        return DEFAULT_MIMETYPE

    @property
    def _request_begin_lifecycle_decorator(self):
        """
        Transforms the result of the operation handler in a internal
        representation (connexion.lifecycle.ConnexionRequest) to be
        used by internal Connexion decorators.

        :rtype: types.FunctionType
        """
        return BeginOfRequestLifecycleDecorator(self.api, self.get_mimetype())

    @property
    def _request_end_lifecycle_decorator(self):
        """
        Guarantees that instead of the internal representation of the
        operation handler response
        (connexion.lifecycle.ConnexionRequest) a framework specific
        object is returned.
        :rtype: types.FunctionType
        """
        return EndOfRequestLifecycleDecorator(self.api, self.get_mimetype())
