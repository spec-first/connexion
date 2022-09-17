import abc
import logging
import pathlib
import typing as t

import typing_extensions as te
from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.abstract import AbstractSpecAPI
from connexion.exceptions import MissingMiddleware
from connexion.http_facts import METHODS
from connexion.operations import AbstractOperation
from connexion.resolver import ResolverError

logger = logging.getLogger("connexion.middleware.abstract")

ROUTING_CONTEXT = "connexion_routing"


class AppMiddleware(abc.ABC):
    """Middlewares that need the APIs to be registered on them should inherit from this base
    class"""

    @abc.abstractmethod
    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        pass


class RoutedOperation(te.Protocol):
    def __init__(self, next_app: ASGIApp, **kwargs) -> None:
        ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...


OP = t.TypeVar("OP", bound=RoutedOperation)


class RoutedAPI(AbstractSpecAPI, t.Generic[OP]):

    operation_cls: t.Type[OP]
    """The operation this middleware uses, which should implement the RoutingOperation protocol."""

    def __init__(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        *args,
        next_app: ASGIApp,
        **kwargs,
    ) -> None:
        super().__init__(specification, *args, **kwargs)
        self.next_app = next_app
        self.operations: t.MutableMapping[str, OP] = {}

    def add_paths(self) -> None:
        paths = self.specification.get("paths", {})
        for path, methods in paths.items():
            for method in methods:
                if method not in METHODS:
                    continue
                try:
                    self.add_operation(path, method)
                except ResolverError:
                    # ResolverErrors are either raised or handled in routing middleware.
                    pass

    def add_operation(self, path: str, method: str) -> None:
        operation_spec_cls = self.specification.operation_cls
        operation = operation_spec_cls.from_spec(
            self.specification, self, path, method, self.resolver
        )
        routed_operation = self.make_operation(operation)
        self.operations[operation.operation_id] = routed_operation

    @abc.abstractmethod
    def make_operation(self, operation: AbstractOperation) -> OP:
        """Create an operation of the `operation_cls` type."""
        raise NotImplementedError


API = t.TypeVar("API", bound="RoutedAPI")


class RoutedMiddleware(AppMiddleware, t.Generic[API]):
    """Baseclass for middleware that wants to leverage the RoutingMiddleware to route requests to
    its operations.

    The RoutingMiddleware adds the operation_id to the ASGI scope. This middleware registers its
    operations by operation_id at startup. At request time, the operation is fetched by an
    operation_id lookup.
    """

    @property
    @abc.abstractmethod
    def api_cls(self) -> t.Type[API]:
        """The subclass of RoutedAPI this middleware uses."""
        raise NotImplementedError

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, API] = {}

    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        api = self.api_cls(specification, next_app=self.app, **kwargs)
        self.apis[api.base_path] = api

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Fetches the operation related to the request and calls it."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            connexion_context = scope["extensions"][ROUTING_CONTEXT]
        except KeyError:
            # TODO: update message
            raise MissingMiddleware(
                "Could not find routing information in scope. Please make sure "
                "you have a routing middleware registered upstream. "
            )
        api_base_path = connexion_context.get("api_base_path")
        if api_base_path:
            api = self.apis[api_base_path]
            operation_id = connexion_context.get("operation_id")
            try:
                operation = api.operations[operation_id]
            except KeyError as e:
                if operation_id is None:
                    logger.debug("Skipping validation check for operation without id.")
                    await self.app(scope, receive, send)
                    return
                else:
                    raise MissingOperation("Encountered unknown operation_id.") from e
            else:
                return await operation(scope, receive, send)

        await self.app(scope, receive, send)


class MissingOperation(Exception):
    """Missing operation"""
