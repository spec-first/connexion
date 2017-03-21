import logging

from .operation import Operation, SecureOperation
from .problem import problem

logger = logging.getLogger('connexion.handlers')


class AuthErrorHandler(SecureOperation):
    """
    Wraps an error with authentication.
    """

    def __init__(self, exception, security, security_definitions, trusted_ips=None):
        """
        This class uses the exception instance to produce the proper response problem in case the
        request is authenticated.

        :param exception: the exception to be wrapped with authentication
        :type exception: werkzeug.exceptions.HTTPException
        :param security: list of security rules the application uses by default
        :type security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        :param trusted_ips: A list of trusted IPs. If request.remote_addr is in this list (i.e. it's a proxy we control)
        then we'll also trust the X-Forwarded-For HTTP header.
        :type trusted_ips: list
        """
        self.exception = exception
        trusted_ips = trusted_ips or []
        SecureOperation.__init__(self, security, security_definitions, trusted_ips)

    @property
    def function(self):
        """
        Configured error auth handler.
        """
        security_decorator = self.security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator, extra=vars(self))
        function = self.handle
        function = self._request_begin_lifecycle_decorator(function)
        function = security_decorator(function)
        function = self._request_end_lifecycle_decorator(function)
        return function

    def handle(self, *args, **kwargs):
        """
        Actual handler for the execution after authentication.
        """
        response_container = problem(
            title=self.exception.name,
            detail=self.exception.description,
            status=self.exception.code
        )
        return response_container


class ResolverErrorHandler(Operation):
    """
    Handler for responding to ResolverError.
    """

    def __init__(self, status_code, exception, *args, **kwargs):
        self.status_code = status_code
        self.exception = exception
        Operation.__init__(self, *args, **kwargs)

    @property
    def function(self):
        return self.handle

    def handle(self, *args, **kwargs):
        response_container = problem(
            title='Not Implemented',
            detail=self.exception.reason,
            status=self.status_code
        )
        return response_container.flask_response_object()
