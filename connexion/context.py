from contextvars import ContextVar

from starlette.types import Scope

_scope: ContextVar[Scope] = ContextVar("SCOPE")


def __getattr__(name):
    if name == "scope":
        return _scope.get()
    if name == "context":
        return _scope.get().get("extensions", {}).get("connexion_context", {})
