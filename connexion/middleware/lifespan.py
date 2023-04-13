import typing as t

from starlette.routing import Router
from starlette.types import ASGIApp, Receive, Scope, Send

Lifespan = t.Callable[[t.Any], t.AsyncContextManager]


class LifespanMiddleware:
    """
    Middleware that adds support for Starlette lifespan handlers
    (https://www.starlette.io/lifespan/).
    """

    def __init__(self, next_app: ASGIApp, *, lifespan: t.Optional[Lifespan]) -> None:
        self.next_app = next_app
        self._lifespan = lifespan
        # Leverage a Starlette Router for lifespan handling only
        self.router = Router(lifespan=lifespan)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # If no lifespan is registered, pass to next app so it can be handled downstream.
        if scope["type"] == "lifespan" and self._lifespan:
            await self.router(scope, receive, send)
        else:
            await self.next_app(scope, receive, send)
