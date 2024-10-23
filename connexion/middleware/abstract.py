import abc
import logging
import typing as t
from collections import defaultdict

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import MissingMiddleware, ResolverError
from connexion.http_facts import METHODS
from connexion.operations import AbstractOperation
from connexion.resolver import Resolver
from connexion.spec import Specification

logger = logging.getLogger(__name__)

ROUTING_CONTEXT = "connexion_routing"


class SpecMiddleware(abc.ABC):
    """Middlewares that need the specification(s) to be registered on them should inherit from this
    base class"""

    @abc.abstractmethod
    def add_api(self, specification: Specification, **kwargs) -> t.Any:
        """
        Register an API represented by a single OpenAPI specification on this middleware.
        Multiple APIs can be registered on a single middleware.
        """

    @abc.abstractmethod
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        pass


class AbstractSpecAPI:
    """Base API class with only minimal behavior related to the specification."""

    def __init__(
        self,
        specification: Specification,
        base_path: t.Optional[str] = None,
        resolver: t.Optional[Resolver] = None,
        uri_parser_class=None,
        *args,
        **kwargs,
    ):
        self.specification = specification
        self.uri_parser_class = uri_parser_class

        self._set_base_path(base_path)

        self.resolver = resolver or Resolver()

    def _set_base_path(self, base_path: t.Optional[str] = None) -> None:
        if base_path is not None:
            # update spec to include user-provided base_path
            self.specification.base_path = base_path
            self.base_path = base_path
        else:
            self.base_path = self.specification.base_path


OP = t.TypeVar("OP")
"""Typevar representing an operation"""


class AbstractRoutingAPI(AbstractSpecAPI, t.Generic[OP]):
    """Base API class with shared functionality related to routing."""

    def __init__(
        self,
        *args,
        pythonic_params=False,
        resolver_error_handler: t.Optional[t.Callable] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.pythonic_params = pythonic_params
        self.resolver_error_handler = resolver_error_handler

        self.add_paths()

    def add_paths(self, paths: t.Optional[dict] = None) -> None:
        """
        Adds the paths defined in the specification as operations.
        """
        paths = t.cast(dict, paths or self.specification.get("paths", dict()))
        for path, methods in paths.items():
            logger.debug("Adding %s%s...", self.base_path, path)

            for method in methods:
                if method not in METHODS:
                    continue
                try:
                    self.add_operation(path, method)
                except ResolverError as err:
                    # If we have an error handler for resolver errors, add it as an operation.
                    # Otherwise treat it as any other error.
                    if self.resolver_error_handler is not None:
                        self._add_resolver_error_handler(method, path, err)
                    else:
                        self._handle_add_operation_error(path, method, err)
                except Exception as e:
                    # All other relevant exceptions should be handled as well.
                    self._handle_add_operation_error(path, method, e)

    def add_operation(self, path: str, method: str) -> None:
        """
        Adds one operation to the api.

        This method uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.
        """
        spec_operation_cls = self.specification.operation_cls
        spec_operation = spec_operation_cls.from_spec(
            self.specification,
            path=path,
            method=method,
            resolver=self.resolver,
            uri_parser_class=self.uri_parser_class,
        )
        operation = self.make_operation(spec_operation)
        path, name = self._framework_path_and_name(spec_operation, path)
        self._add_operation_internal(method, path, operation, name=name)

    @abc.abstractmethod
    def make_operation(self, operation: AbstractOperation) -> OP:
        """Build an operation to register on the API."""

    @staticmethod
    def _framework_path_and_name(
        operation: AbstractOperation, path: str
    ) -> t.Tuple[str, str]:
        """Prepare the framework path & name to register the operation on the API."""

    @abc.abstractmethod
    def _add_operation_internal(
        self, method: str, path: str, operation: OP, name: t.Optional[str] = None
    ) -> None:
        """
        Adds the operation according to the user framework in use.
        It will be used to register the operation on the user framework router.
        """

    def _add_resolver_error_handler(
        self, method: str, path: str, err: ResolverError
    ) -> None:
        """
        Adds a handler for ResolverError for the given method and path.
        """
        self.resolver_error_handler = t.cast(t.Callable, self.resolver_error_handler)
        operation = self.resolver_error_handler(
            err,
        )
        self._add_operation_internal(method, path, operation)

    def _handle_add_operation_error(
        self, path: str, method: str, exc: Exception
    ) -> None:
        url = f"{self.base_path}{path}"
        error_msg = f"Failed to add operation for {method.upper()} {url}"
        logger.error(error_msg)
        raise exc from None


class RoutedAPI(AbstractSpecAPI, t.Generic[OP]):
    def __init__(
        self,
        specification: Specification,
        *args,
        next_app: ASGIApp,
        **kwargs,
    ) -> None:
        super().__init__(specification, *args, **kwargs)
        self.next_app = next_app
        self.operations: t.MutableMapping[t.Optional[str], OP] = {}

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
            self.specification,
            path=path,
            method=method,
            resolver=self.resolver,
            uri_parser_class=self.uri_parser_class,
        )
        routed_operation = self.make_operation(operation)
        self.operations[operation.operation_id] = routed_operation

    @abc.abstractmethod
    def make_operation(self, operation: AbstractOperation) -> OP:
        """Create an operation of the `operation_cls` type."""
        raise NotImplementedError


API = t.TypeVar("API", bound="RoutedAPI")
"""Typevar representing an API which subclasses RoutedAPI"""


class RoutedMiddleware(SpecMiddleware, t.Generic[API]):
    """Baseclass for middleware that wants to leverage the RoutingMiddleware to route requests to
    its operations.

    The RoutingMiddleware adds the operation_id to the ASGI scope. This middleware registers its
    operations by operation_id at startup. At request time, the operation is fetched by an
    operation_id lookup.
    """

    api_cls: t.Type[API]
    """The subclass of RoutedAPI this middleware uses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, t.List[API]] = defaultdict(list)

    def add_api(self, specification: Specification, **kwargs) -> API:
        api = self.api_cls(specification, next_app=self.app, **kwargs)
        self.apis[api.base_path].append(api)
        return api

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Fetches the operation related to the request and calls it."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            connexion_context = scope["extensions"][ROUTING_CONTEXT]
        except KeyError:
            raise MissingMiddleware(
                "Could not find routing information in scope. Please make sure "
                "you have a routing middleware registered upstream. "
            )
        api_base_path = connexion_context.get("api_base_path")
        if api_base_path is not None and api_base_path in self.apis:
            for api in self.apis[api_base_path]:
                operation_id = connexion_context.get("operation_id")
                try:
                    operation = api.operations[operation_id]
                except KeyError:
                    if operation_id is None:
                        logger.debug("Skipping operation without id.")
                        await self.app(scope, receive, send)
                        return
                else:
                    return await operation(scope, receive, send)

            raise MissingOperation("Encountered unknown operation_id.")

        await self.app(scope, receive, send)


class MissingOperation(Exception):
    """Missing operation"""
