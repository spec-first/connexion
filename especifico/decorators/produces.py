"""
This module defines decorators to change the return type of a view function.
"""

import functools
import logging

from .decorator import BaseDecorator

logger = logging.getLogger("especifico.decorators.produces")

# special marker object to return empty content for any status code
# e.g. in app method do "return NoContent, 201"
NoContent = object()


class BaseSerializer(BaseDecorator):
    def __init__(self, mimetype="text/plain"):
        """
        :type mimetype: str
        """
        self.mimetype = mimetype

    def __repr__(self):
        """
        :rtype: str
        """
        return f"<BaseSerializer: {self.mimetype}>"  # pragma: no cover


class Produces(BaseSerializer):
    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            url = request.url
            response = function(request)
            logger.debug("Returning %s", url, extra={"url": url, "mimetype": self.mimetype})
            return response

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return f"<Produces: {self.mimetype}>"  # pragma: no cover
