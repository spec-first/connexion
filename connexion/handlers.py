
import logging
from .operation import SecureOperation
from .problem import problem

logger = logging.getLogger('connexion.handlers')


class AuthErrorHandler(SecureOperation):
    def __init__(self, exception, security, security_definitions):
        self.exception = exception
        self.security = security
        self.security_definitions = security_definitions

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
