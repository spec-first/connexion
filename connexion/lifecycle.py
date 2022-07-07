"""
This module defines interfaces for requests and responses used in Connexion for authentication,
validation, serialization, etc.
"""
import typing as t

from starlette.requests import Request as StarletteRequest
from starlette.responses import StreamingResponse as StarletteStreamingResponse
from starlette.types import Receive, Scope

from connexion.decorators.uri_parsing import AbstractURIParser


class ConnexionRequest:
    """Connexion interface for a request."""

    def __init__(
        self,
        url,
        method,
        path_params=None,
        query=None,
        headers=None,
        form=None,
        body=None,
        json_getter=None,
        files=None,
        context=None,
        cookies=None,
    ):
        self.url = url
        self.method = method
        self.path_params = path_params or {}
        self.query = query or {}
        self.headers = headers or {}
        self.form = form or {}
        self.body = body
        self.json_getter = json_getter
        self.files = files
        self.context = context if context is not None else {}
        self.cookies = cookies or {}

    @property
    def json(self):
        if not hasattr(self, "_json"):
            self._json = self.json_getter()
        return self._json


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


class MiddlewareRequest:
    """Wraps starlette Request so it can easily be extended."""

    def __init__(self, scope: Scope, receive: Receive = None, uri_parser: AbstractURIParser = None):
        self._scope = scope
        self._request = StarletteRequest(scope, receive)
        self.uri_parser = uri_parser

    @property
    def query(self):
        if not hasattr(self, "_query"):
            query_params = dict(self._request.query_params.items())
            self._query = self.uri_parser.resolve_query(query_params)
        return self._query

    @property
    def path_params(self) -> dict:
        if not hasattr(self, "_path_params"):
            path_params = self._request.path_params
            self._path_params = self.uri_parser.resolve_path(path_params)
        return self._path_params

    @property
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            self._body = await self._request.body()
        return self._body

    @property
    async def form(self) -> dict:
        if not hasattr(self, "_form"):
            form_data = await self._request.form()
            self._form = self.uri_parser.resolve_form(form_data)
        return self._form

    @property
    def context(self):
        if not hasattr(self, "._context"):
            extensions = self._scope.setdefault("extensions", {})
            self._context = extensions.setdefault("connexion_context", {})
        return self._context

    @property
    async def json(self):
        if not hasattr(self, "_json"):
            self._json = await self._request.json() if await self.body else None
        return self._json

    @property
    def files(self):
        return {}  # TODO

    @property
    def headers(self):
        return self._request.headers


class MiddlewareResponse(StarletteStreamingResponse):
    """Wraps starlette StreamingResponse so it can easily be extended."""
