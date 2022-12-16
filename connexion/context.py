from asyncio import AbstractEventLoop
from contextvars import ContextVar

_context: ContextVar[AbstractEventLoop] = ContextVar("CONTEXT")


def __getattr__(name):
    if name == "context":
        return _context.get()
