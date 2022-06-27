"""
Validation Middleware.
"""
import logging
import pathlib
import typing as t

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.abstract import AbstractSpecAPI
from connexion.exceptions import MissingMiddleware, ResolverError
from connexion.http_facts import METHODS
from connexion.middleware import AppMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from connexion.operations.abstract import AbstractOperation

logger = logging.getLogger("connexion.middleware.validation")


# TODO: split up Request parsing/validation and response parsing/validation?
#   response validation as separate middleware to allow easy decoupling and disabling/enabling?
class ValidationMiddleware(AppMiddleware):

    """Middleware for validating requests according to the API contract."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, ValidationAPI] = {}

    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        api = ValidationAPI(specification, **kwargs)
        self.apis[api.base_path] = api

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
        if api_base_path:
            api = self.apis[api_base_path]
            operation_id = connexion_context.get("operation_id")
            try:
                _ = api.operations[operation_id]
            except KeyError as e:
                if operation_id is None:
                    logger.debug("Skipping validation check for operation without id.")
                else:
                    raise MissingValidationOperation(
                        "Encountered unknown operation_id."
                    ) from e
            else:
                # TODO: Add validation logic
                pass

        await self.app(scope, receive, send)


class ValidationAPI(AbstractSpecAPI):
    """Validation API."""

    def __init__(
        self, specification: t.Union[pathlib.Path, str, dict], *args, **kwargs
    ):
        super().__init__(specification, *args, **kwargs)

        self.operations: t.Dict[str, ValidationOperation] = {}
        self.add_paths()

    def add_paths(self):
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
        operation_cls = self.specification.operation_cls
        operation = operation_cls.from_spec(
            self.specification, self, path, method, self.resolver
        )
        validation_operation = self.make_operation(operation)
        self._add_operation_internal(operation.operation_id, validation_operation)

    def make_operation(self, operation: AbstractOperation):
        return ValidationOperation.from_operation(
            operation,
        )

    def _add_operation_internal(
        self, operation_id: str, operation: "ValidationOperation"
    ):
        self.operations[operation_id] = operation


class ValidationOperation:
    def __init__(self) -> None:
        pass

    @classmethod
    def from_operation(cls, operation):
        return cls()


class MissingValidationOperation(Exception):
    """Missing validation operation"""
