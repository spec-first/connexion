"""
This module defines a RequestResponseDecorator
which manages the lifecycle of a request internally in Connexion.
"""

import asyncio
import functools
import logging
import typing as t

from connexion.uri_parsing import AbstractURIParser
from connexion.utils import has_coroutine

logger = logging.getLogger("connexion.decorators.decorator")


class RequestResponseDecorator:
    """Manages the lifecycle of the request internally in Connexion.
    Filter the ConnexionRequest instance to return the corresponding
    framework specific object.
    """

    def __init__(self, api, mimetype):
        self.api = api
        self.mimetype = mimetype

    def __call__(
        self, function: t.Callable, uri_parser: AbstractURIParser = None
    ) -> t.Callable:
        if has_coroutine(function, self.api):

            @functools.wraps(function)
            async def wrapper(*args, **kwargs):
                connexion_request = self.api.get_request(
                    *args, uri_parser=uri_parser, **kwargs
                )
                while asyncio.iscoroutine(connexion_request):
                    connexion_request = await connexion_request

                connexion_response = function(connexion_request)
                while asyncio.iscoroutine(connexion_response):
                    connexion_response = await connexion_response

                framework_response = self.api.get_response(
                    connexion_response, self.mimetype
                )
                while asyncio.iscoroutine(framework_response):
                    framework_response = await framework_response

                return framework_response

        else:  # pragma: no cover

            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                request = self.api.get_request()
                response = function(request)
                return self.api.get_response(response, self.mimetype)

        return wrapper
