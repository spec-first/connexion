"""
Module that monkey patches a2wsgi to make contextvars available to the WSGI application.
This can be removed once https://github.com/abersheeran/a2wsgi/pull/31 is merged.
"""
import contextvars
import functools

import a2wsgi.wsgi
from a2wsgi.wsgi import WSGIResponder


class ContextWSGIResponder(WSGIResponder):
    """Custom Responder that makes contextvars available to the WSGI application."""

    @property
    def wsgi(self):
        context = contextvars.copy_context()
        return functools.partial(context.run, super().wsgi)


# Monkeypatch module with our custom Responder
a2wsgi.wsgi.WSGIResponder = ContextWSGIResponder

# Import the WSGIMiddleware now so it uses our custom Responder
from a2wsgi import WSGIMiddleware  # NOQA
