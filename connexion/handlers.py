"""
This module defines error handlers, operations that produce proper response problems.
"""

import logging

from .exceptions import ResolverProblem

logger = logging.getLogger("connexion.handlers")

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
            detail=self.exception.args[0],
            status=self.status_code,
        )

    @property
    def operation_id(self):
        return "noop"

    @property
    def randomize_endpoint(self):
        return RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS

    def get_path_parameter_types(self):
        return {}

    @property
    def uri_parser_class(self):
        return "dummy"

    @property
    def api(self):
        return "dummy"

    def get_mimetype(self):
        return "dummy"

    async def __call__(self, *args, **kwargs):
        raise ResolverProblem(
            detail=self.exception.args[0],
            status=self.status_code,
        )
