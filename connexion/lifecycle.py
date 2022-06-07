"""
This module defines interfaces for requests and responses used in Connexion for authentication,
validation, serialization, etc.
"""
import typing as t

from starlette.requests import ClientDisconnect, Request as StarletteRequest
from starlette.responses import StreamingResponse as StarletteStreamingResponse


class ConnexionRequest:
    """Connexion interface for a request."""
    def __init__(self,
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
                 cookies=None):
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
        if not hasattr(self, '_json'):
            self._json = self.json_getter()
        return self._json


class ConnexionResponse:
    """Connexion interface for a response."""
    def __init__(self,
                 status_code=200,
                 mimetype=None,
                 content_type=None,
                 body=None,
                 headers=None,
                 is_streamed=False):
        self.status_code = status_code
        self.mimetype = mimetype
        self.content_type = content_type
        self.body = body
        self.headers = headers or {}
        self.is_streamed = is_streamed


class MiddlewareRequest(StarletteRequest):
    """Wraps starlette Request so it can easily be extended."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = None

    @property
    def context(self):
        if self._context is None:
            extensions = self.scope.setdefault('extensions', {})
            self._context = extensions.setdefault('connexion_context', {})

        return self._context


class BodyMiddlewareRequest(MiddlewareRequest):
    """Middleware request that reads the body and stores it in the ASGI scope.
    
    See also: https://github.com/encode/starlette/pull/1519
    """

    # Not particularly graceful, but we store state around reading the request
    # body in the ASGI scope, under the following...
    #
    # ['extensions']['starlette']['body']
    # ['extensions']['starlette']['stream_consumed']
    #
    # This allows usages such as ASGI middleware to call the recieve and
    # access the request body, and have that state persisted.
    #
    # Bit of an abuse of ASGI to take this approach. An alternate take would be
    # that if you're going to use ASGI middleware it might be better to just
    # accept the constraint that you *don't* get access to the request body in
    # that context.
    def _get_request_state(self, name: str, default: t.Any = None) -> t.Any:
        return self.scope.get("extensions", {}).get("starlette", {}).get(name, default)

    def _set_request_state(self, name: str, value: t.Any) -> None:
        if "extensions" not in self.scope:
            self.scope["extensions"] = {"starlette": {name: value}}
        elif "starlette" not in self.scope["extensions"]:
            self.scope["extensions"]["starlette"] = {name: value}
        else:
            self.scope["extensions"]["starlette"][name] = value

    async def stream(self) -> t.AsyncGenerator[bytes, None]:
        body = self._get_request_state("body")
        if body is not None:
            yield body
            yield b""
            return

        stream_consumed = self._get_request_state("stream_consumed", default=False)
        if stream_consumed:
            raise RuntimeError("Stream consumed")

        self._set_request_state("stream_consumed", True)
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    yield body
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                self._is_disconnected = True
                raise ClientDisconnect()
        yield b""

    async def body(self) -> bytes:
        body = self._get_request_state("body")
        if body is None:
            chunks = []
            async for chunk in self.stream():
                chunks.append(chunk)
            body = b"".join(chunks)
            self._set_request_state("body", body)
        return body

# TODO: Need other kind of response class to easily retrieve response body?
#   The regular starlette Response class?
class MiddlewareResponse(StarletteStreamingResponse):
    """Wraps starlette StreamingResponse so it can easily be extended."""
