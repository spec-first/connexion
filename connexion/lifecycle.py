"""
This module defines interfaces for requests and responses used in Connexion for authentication,
validation, serialization, etc.
"""
import typing as t

from flask import Request as FlaskRequest
from starlette.requests import Request as StarletteRequest
from starlette.responses import StreamingResponse as StarletteStreamingResponse


class ConnexionResponse:
    """Connexion interface for a response."""

    def __init__(
        self,
        status_code=200,
        mimetype=None,
        content_type=None,
        body=None,
        headers=None,
        is_streamed=False,
    ):
        self.status_code = status_code
        self.mimetype = mimetype
        self.content_type = content_type
        self.body = body
        self.headers = headers or {}
        self.is_streamed = is_streamed


class ConnexionRequest:
    def __init__(self, flask_request: FlaskRequest, uri_parser=None):
        self._flask_request = flask_request
        self.uri_parser = uri_parser
        self._context = None

    @property
    def context(self):
        if self._context is None:
            scope = self._flask_request.environ["asgi.scope"]
            extensions = scope.setdefault("extensions", {})
            self._context = extensions.setdefault("connexion_context", {})

        return self._context

    @property
    def view_args(self) -> t.Dict[str, t.Any]:
        return self.uri_parser.resolve_path(self._flask_request.view_args)

    @property
    def args(self):
        query_params = self._flask_request.args
        query_params = {k: query_params.getlist(k) for k in query_params}
        return self.uri_parser.resolve_query(query_params)

    @property
    def form(self):
        form = self._flask_request.form.to_dict(flat=False)
        form_data = self.uri_parser.resolve_form(form)
        return form_data

    def __getattr__(self, item):
        return getattr(self._flask_request, item)


class MiddlewareRequest(StarletteRequest):
    """Wraps starlette Request so it can easily be extended."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = None

    @property
    def context(self):
        if self._context is None:
            extensions = self.scope.setdefault("extensions", {})
            self._context = extensions.setdefault("connexion_context", {})

        return self._context


class MiddlewareResponse(StarletteStreamingResponse):
    """Wraps starlette StreamingResponse so it can easily be extended."""
