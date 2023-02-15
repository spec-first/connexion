"""
This module defines interfaces for requests and responses used in Connexion for authentication,
validation, serialization, etc.
"""
import typing as t
from collections import defaultdict

from multipart.multipart import parse_options_header
from starlette.datastructures import UploadFile
from starlette.requests import Request as StarletteRequest
from werkzeug import Request as WerkzeugRequest

from connexion.http_facts import FORM_CONTENT_TYPES
from connexion.utils import is_json_mimetype


class _RequestInterface:
    @property
    def context(self) -> t.Dict[str, t.Any]:
        """The connexion context of the current request cycle."""
        raise NotImplementedError

    @property
    def content_type(self) -> str:
        raise NotImplementedError

    @property
    def mimetype(self) -> str:
        raise NotImplementedError

    @property
    def path_params(self) -> t.Dict[str, t.Any]:
        raise NotImplementedError

    @property
    def query_params(self) -> t.Dict[str, t.Any]:
        raise NotImplementedError

    def form(self) -> t.Union[t.Dict[str, t.Any], t.Awaitable[t.Dict[str, t.Any]]]:
        raise NotImplementedError

    def files(self) -> t.Dict[str, t.Any]:
        raise NotImplementedError

    def get_body(self) -> t.Any:
        raise NotImplementedError


class WSGIRequest(_RequestInterface):
    def __init__(
        self, werkzeug_request: WerkzeugRequest, uri_parser=None, view_args=None
    ):
        self._werkzeug_request = werkzeug_request
        self.uri_parser = uri_parser
        self.view_args = view_args

        self._context = None
        self._path_params = None
        self._query_params = None
        self._form = None
        self._body = None

    @property
    def context(self):
        if self._context is None:
            scope = self.environ["asgi.scope"]
            extensions = scope.setdefault("extensions", {})
            self._context = extensions.setdefault("connexion_context", {})
        return self._context

    @property
    def content_type(self) -> str:
        return self._werkzeug_request.content_type or "application/octet-stream"

    @property
    def mimetype(self) -> str:
        return self._werkzeug_request.mimetype

    @property
    def path_params(self):
        if self._path_params is None:
            self._path_params = self.uri_parser.resolve_path(self.view_args)
        return self._path_params

    @property
    def query_params(self):
        if self._query_params is None:
            query_params = {k: self.args.getlist(k) for k in self.args}
            self._query_params = self.uri_parser.resolve_query(query_params)
        return self._query_params

    def form(self):
        if self._form is None:
            form = self._werkzeug_request.form.to_dict(flat=False)
            self._form = self.uri_parser.resolve_form(form)
        return self._form

    def files(self):
        return self._werkzeug_request.files.to_dict(flat=False)

    def get_body(self):
        """Get body based on content type"""
        if self._body is None:
            if is_json_mimetype(self.content_type):
                self._body = self.get_json(silent=True)
            elif self.mimetype in FORM_CONTENT_TYPES:
                self._body = self.form()
            else:
                # Return explicit None instead of empty bytestring so it is handled as null downstream
                self._body = self.get_data() or None
        return self._body

    def __getattr__(self, item):
        return getattr(self._werkzeug_request, item)


class ASGIRequest(_RequestInterface):
    """Wraps starlette Request so it can easily be extended."""

    def __init__(self, *args, uri_parser=None, **kwargs):
        self._starlette_request = StarletteRequest(*args, **kwargs)
        self.uri_parser = uri_parser

        self._context = None
        self._mimetype = None
        self._path_params = None
        self._query_params = None
        self._form = None
        self._files = None

    @property
    def context(self):
        if self._context is None:
            extensions = self.scope.setdefault("extensions", {})
            self._context = extensions.setdefault("connexion_context", {})
        return self._context

    @property
    def content_type(self):
        return self.headers.get("content-type", "application/octet-stream")

    @property
    def mimetype(self):
        if not self._mimetype:
            mimetype, _ = parse_options_header(self.content_type)
            self._mimetype = mimetype.decode()
        return self._mimetype

    @property
    def path_params(self) -> t.Dict[str, t.Any]:
        if self._path_params is None:
            self._path_params = self.uri_parser.resolve_path(
                self._starlette_request.path_params
            )
        return self._path_params

    @property
    def query_params(self):
        if self._query_params is None:
            args = self._starlette_request.query_params
            query_params = {k: args.getlist(k) for k in args}
            self._query_params = self.uri_parser.resolve_query(query_params)
        return self._query_params

    async def form(self):
        if self._form is None:
            await self._split_form_files()
        return self._form

    async def files(self):
        if self._files is None:
            await self._split_form_files()
        return self._files

    async def _split_form_files(self):
        form_data = await self._starlette_request.form()

        files = defaultdict(list)
        form = defaultdict(list)
        for k, v in form_data.multi_items():
            if isinstance(v, UploadFile):
                files[k].append(v)
            else:
                form[k].append(v)

        self._files = files
        self._form = self.uri_parser.resolve_form(form)

    async def json(self):
        try:
            return await self._starlette_request.json()
        except ValueError:
            return None

    async def get_body(self):
        if is_json_mimetype(self.content_type):
            return await self.json()
        elif self.mimetype in FORM_CONTENT_TYPES:
            return await self.form()
        else:
            # Return explicit None instead of empty bytestring so it is handled as null downstream
            return await self.body() or None

    def __getattr__(self, item):
        return getattr(self._starlette_request, item)


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
        self.headers.update({"Content-Type": content_type})
        self.is_streamed = is_streamed
