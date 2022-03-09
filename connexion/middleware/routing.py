import pathlib
import typing as t
from contextvars import ContextVar
from functools import partial

import anyio
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from starlette.routing import Router
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.middleware_api import MiddlewareAPI
from connexion.operations import AbstractOperation
from connexion.resolver import Resolver

# Context variable that is set to starlette call_next function with current request
_call_next_fn: ContextVar[t.Callable] = ContextVar('CALL_NEXT')


async def call_next_callback(operation: AbstractOperation, _request: StarletteRequest) \
        -> StarletteResponse:
    """Callback to call next app with current request."""
    return await _call_next_fn.get()(operation)


class MiddlewareResolver(Resolver):

    def __init__(self, call_next: t.Callable) -> None:
        """Resolver that resolves each operation to the provided call_next function."""
        super().__init__()
        self.call_next = call_next

    def resolve_function_from_operation_id(self, operation_id: str) -> t.Callable:
        return self.call_next


class RoutingMiddleware:

    def __init__(self, app: ASGIApp) -> None:
        """Middleware that resolves the Operation for an incoming request and attaches it to the
        scope.

        :param app: app to wrap in middleware.
        """
        self.app = app
        self.router = Router()

    def add_api(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
    ) -> None:
        """Add an API to the router based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        resolver = MiddlewareResolver(call_next_callback)
        api = MiddlewareAPI(specification, base_path=base_path, arguments=arguments,
                            resolver=resolver)
        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route request to matching operation, and attach it to the scope before calling the
        next app."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        call_next = self._create_call_next(scope)

        async with anyio.create_task_group() as task_group:
            request = StarletteRequest(scope, receive=receive)
            call_next_ = partial(call_next, request, task_group)
            _call_next_fn.set(call_next_)

            await self.router(scope, receive, send)
            await task_group.cancel_scope.cancel()

    def _create_call_next(self, scope: Scope) -> t.Callable:
        """Create callable to call next app."""

        async def call_next(request: StarletteRequest, task_group: anyio.abc.TaskGroup) \
                -> StarletteResponse:
            """Adapted from starlette.middleware.base.BaseHTTPMiddleware"""
            app_exc: t.Optional[Exception] = None
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

            async def body_stream() -> t.AsyncGenerator[bytes, None]:
                async with recv_stream:
                    async for msg in recv_stream:
                        assert msg["type"] == "http.response.body"
                        yield msg.get("body", b"")

                if app_exc is not None:
                    raise app_exc

            response = StreamingResponse(
                status_code=message["status"], content=body_stream()
            )

            response.raw_headers = message["headers"]
            return response

        async def attach_operation_and_call_next(
                request: StarletteRequest,
                task_group: anyio.abc.TaskGroup,
                operation: AbstractOperation
        ) -> StarletteResponse:
            """Attach operation to scope and pass it to the next app"""
            scope["operation"] = operation
            return await call_next(request, task_group)

        return attach_operation_and_call_next
