import functools
import logging

from ..utils import has_coroutine

logger = logging.getLogger('connexion.decorators.decorator')


class BaseDecorator(object):

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        return function

    def __repr__(self):  # pragma: no cover
        """
        :rtype: str
        """
        return '<BaseDecorator>'


class RequestResponseDecorator(BaseDecorator):
    """Manages the lifecycle of the request internally in Connexion.
    Filter the ConnexionRequest instance to return the corresponding
    framework specific object.
    """

    def __init__(self, api, stream_upload, mimetype):
        self.api = api
        self.stream_upload = stream_upload
        self.mimetype = mimetype

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        if has_coroutine(function, self.api):
            from .coroutine_wrappers import get_request_life_cycle_wrapper
            wrapper = get_request_life_cycle_wrapper(function, self.api, self.stream_upload, self.mimetype)

        else:  # pragma: 3 no cover
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                # Pass args and kwargs as a tuple/dict respectively so they don't
                # interfere with the other parameters.
                request = self.api.get_request(self.stream_upload, args, kwargs)
                response = function(request)
                return self.api.get_response(response, self.mimetype, request)

        return wrapper
