"""
This module defines error handlers, operations that produce proper response problems.
"""

import logging

from .exceptions import ResolverProblem

logger = logging.getLogger('connexion.handlers')

RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS = 6


class ResolverErrorHandler:
    """
    Handler for responding to ResolverError.
    """

    def __init__(self, status_code, exception):
        self.status_code = status_code
        self.exception = exception

    @property
    def function(self):
        return self.handle

    def handle(self, *args, **kwargs):
        raise ResolverProblem(
            title='Not Implemented',
            detail=self.exception.reason,
            status=self.status_code
        )

    @property
    def operation_id(self):
        return "noop"

    @property
    def randomize_endpoint(self):
        return RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS

    def get_path_parameter_types(self):
        return {}
