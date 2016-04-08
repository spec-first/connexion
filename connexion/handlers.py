
import logging

from .operation import SecureOperation
from .problem import problem

logger = logging.getLogger('connexion.handlers')


class AuthErrorHandler(SecureOperation):
    """
    Wraps an error with authentication.
    """

    def __init__(self, exception, security, security_definitions):
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
        """
        self.exception = exception
        SecureOperation.__init__(self, security, security_definitions)

    @property
    def function(self):
        """
        Configured error auth handler.
        """
        security_decorator = self.security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator, extra=vars(self))
        return security_decorator(self.handle)

    def handle(self, *args, **kwargs):
        """
        Actual handler for the execution after authentication.
        """
        return problem(title=self.exception.name, detail=self.exception.description, status=self.exception.code)
