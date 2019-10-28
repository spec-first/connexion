from ..utils import get_tracer
import logging

logger = logging.getLogger('')


def TracerDecorator(func):
    def wrapper(response, mimetype=None, request=None):
        #don't need to check, because this Decorator will only be executed, if the tracer was configured at startup
        tracer = get_tracer()

        from opentracing.ext import tags
        from opentracing.propagation import Format

        # extract the context from request header to continue a session
        # taken from https://github.com/yurishkuro/opentracing-tutorial/tree/master/python/lesson03#extract-the-span-context-from-the-incoming-request-using-tracerextract
        if request is not None:
            span_ctx = tracer.extract(Format.HTTP_HEADERS, request.headers)
            span_tags = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}

            # remove domain from url, so only the path is in the span
            from urllib.parse import urlparse
            path = urlparse(request.url).path

            scope = tracer.start_span(request.method + "_" + path, child_of=span_ctx, tags=span_tags)
            scope.log_kv({"request": request})
        else:
            scope = tracer.start_span("NO_REQUEST_CONTEXT")

        resp = func(response, mimetype, request)

        scope.log_kv({"response": response})
        scope.finish()

        return resp

    return wrapper
