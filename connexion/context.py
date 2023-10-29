from contextvars import ContextVar

from starlette.types import Receive, Scope
from werkzeug.local import LocalProxy

from connexion.lifecycle import ConnexionRequest
from connexion.operations import AbstractOperation

UNBOUND_MESSAGE = (
    "Working outside of operation context. Make sure your app is wrapped in a "
    "ContextMiddleware and you're processing a request while accessing the context."
)


_context: ContextVar[dict] = ContextVar("CONTEXT")
context = LocalProxy(_context, unbound_message=UNBOUND_MESSAGE)

_operation: ContextVar[AbstractOperation] = ContextVar("OPERATION")
operation = LocalProxy(_operation, unbound_message=UNBOUND_MESSAGE)

_receive: ContextVar[Receive] = ContextVar("RECEIVE")
receive = LocalProxy(_receive, unbound_message=UNBOUND_MESSAGE)

_scope: ContextVar[Scope] = ContextVar("SCOPE")
scope = LocalProxy(_scope, unbound_message=UNBOUND_MESSAGE)

request = LocalProxy(
    lambda: ConnexionRequest(scope, receive), unbound_message=UNBOUND_MESSAGE
)
