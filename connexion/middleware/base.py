import typing
from urllib.parse import parse_qs

import anyio
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.operations import AbstractOperation

RequestResponseEndpoint = typing.Callable[[StarletteRequest], typing.Awaitable[StreamingResponse]]
DispatchFunction = typing.Callable[
    [StarletteRequest, AbstractOperation, RequestResponseEndpoint],
    typing.Awaitable[StarletteResponse]
]


class BaseHTTPMiddleware:

    def __init__(self, app: ASGIApp, dispatch: DispatchFunction = None) -> None:
        """Base Middleware to subclass. Provides easy access to request and operation."""
        self.app = app
        self.dispatch_func = self.dispatch if dispatch is None else dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def call_next(request: StarletteRequest) -> StarletteResponse:
            app_exc: typing.Optional[Exception] = None
            send_stream, recv_stream = anyio.create_memory_object_stream()

            async def coro() -> None:
                nonlocal app_exc

                async with send_stream:
                    try:
                        await self.app(scope, request.receive, send_stream.send)
                    except Exception as exc:
                        app_exc = exc

            task_group.start_soon(coro)

            try:
                message = await recv_stream.receive()
            except anyio.EndOfStream:
                if app_exc is not None:
                    raise app_exc
                raise RuntimeError("No response returned.")

            assert message["type"] == "http.response.start"

            async def body_stream() -> typing.AsyncGenerator[bytes, None]:
                async with recv_stream:
                    async for message in recv_stream:
                        assert message["type"] == "http.response.body"
                        yield message.get("body", b"")

                if app_exc is not None:
                    raise app_exc

            response = StreamingResponse(
                status_code=message["status"], content=body_stream()
            )
            response.raw_headers = message["headers"]
            return response

        async with anyio.create_task_group() as task_group:
            request = StarletteRequest(scope, receive=receive)
            # request = await self.starlette_to_connexion_request(request)
            request = transform_request(request)
            operation = scope["operation"]
            response = await self.dispatch_func(request, operation, call_next)
            await response(scope, receive, send)
            await task_group.cancel_scope.cancel()

    async def dispatch(
        self,
            request: StarletteRequest,
            operation: AbstractOperation,
            call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """Function to implement in subclass.

        def dispatch(...):
            # Manipulate request
            response = await call_next(request)
            # Manipulate response
            return response

        :param request: Incoming request.
        :param operation: Operation matching the incoming request.
        :param call_next: Utility function to call then next App.

        :return: Manipulated response
        """
        raise NotImplementedError()  # pragma: no cover


def transform_request(req: StarletteRequest) -> StarletteRequest:
    # TODO: cast to connexion request instead
    req.query = parse_qs(req.url.query)
    req.context = {}
    return req
