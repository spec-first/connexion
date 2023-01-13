import contextvars
import typing as t
from unittest.mock import MagicMock

from starlette.types import Receive, Scope

from connexion.context import _context, _operation, _receive, _scope
from connexion.operations import AbstractOperation


class TestContext:
    __test__ = False  # Pytest

    def __init__(
        self,
        *,
        context: dict = None,
        operation: AbstractOperation = None,
        receive: Receive = None,
        scope: Scope = None,
    ) -> None:
        self.context = context if context is not None else self.build_context()
        self.operation = operation if operation is not None else self.build_operation()
        self.receive = receive if receive is not None else self.build_receive()
        self.scope = scope if scope is not None else self.build_scope()

        self.tokens: t.Dict[str, contextvars.Token] = {}

    def __enter__(self) -> None:
        self.tokens["context"] = _context.set(self.context)
        self.tokens["operation"] = _operation.set(self.operation)
        self.tokens["receive"] = _receive.set(self.receive)
        self.tokens["scope"] = _scope.set(self.scope)
        return

    def __exit__(self, type, value, traceback):
        _context.reset(self.tokens["context"])
        _operation.reset(self.tokens["operation"])
        _receive.reset(self.tokens["receive"])
        _scope.reset(self.tokens["scope"])
        return False

    @staticmethod
    def build_context() -> dict:
        return {}

    @staticmethod
    def build_operation() -> AbstractOperation:
        return MagicMock(name="operation")

    @staticmethod
    def build_receive() -> Receive:
        async def receive() -> t.MutableMapping[str, t.Any]:
            return {
                "type": "http.request",
                "body": b"",
            }

        return receive

    @staticmethod
    def build_scope(**kwargs) -> Scope:
        scope = {
            "type": "http",
            "query_string": b"",
            "headers": [(b"Content-Type", b"application/octet-stream")],
        }

        for key, value in kwargs.items():
            scope[key] = value

        return scope
