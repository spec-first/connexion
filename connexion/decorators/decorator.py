import functools
import logging

from ..utils import has_coroutine, jaeger

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

    def __init__(self, api, mimetype):
        self.api = api
        self.mimetype = mimetype

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        
        # if jaeger is configured, then start a span now
        if jaeger:
            from opentracing.ext import tags
            
            # extract the context from request header to continue a session
            # taken from https://github.com/yurishkuro/opentracing-tutorial/tree/master/python/lesson03#extract-the-span-context-from-the-incoming-request-using-tracerextract
            request = self.api.get_request(*args, **kwargs)
            span_ctx = tracer.extract(Format.HTTP_HEADERS, request.headers)
            span_tags = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
            
            span = tracer.start_active_span('RequestResponseDecorator', child_of=span_ctx, tags=span_tags)
            span.log_kv({"request": request})
                                        
        if has_coroutine(function, self.api):  # pragma: 2.7 no cover
            from .coroutine_wrappers import get_request_life_cycle_wrapper
            wrapper = get_request_life_cycle_wrapper(function, self.api, self.mimetype)

        else:  # pragma: 3 no cover
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                request = self.api.get_request(*args, **kwargs)
                response = function(request)
                return self.api.get_response(response, self.mimetype, request)

        # if jaeger and a span are configured, finish it now.
        if jaeger and span:
            span.log_kv({"response": wrapper.response})
            span.finish()
            
        return wrapper
