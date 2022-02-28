import pathlib
import typing as t

from starlette.routing import Router

from connexion.apis import AbstractMinimalAPI
from connexion.operations import make_operation, AbstractOperation
from connexion.resolver import Resolver
from connexion.security import MiddlewareSecurityHandlerFactory


class MiddlewareAPI(AbstractMinimalAPI):

    def __init__(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
            resolver: t.Optional[Resolver] = None,
            resolver_error_handler: t.Optional[t.Callable] = None,
            debug: bool = False,
    ) -> None:
        """API implementation on top of Starlette Router for Connexion middleware."""
        self.router = Router()

        super().__init__(
            specification,
            base_path=base_path,
            arguments=arguments,
            resolver=resolver,
            resolver_error_handler=resolver_error_handler,
            debug=debug
        )

    def add_operation(self, path: str, method: str) -> None:
        operation = make_operation(
            self.specification,
            self,
            path,
            method,
            self.resolver
        )
        # Don't set decorators in middleware
        AbstractOperation.function = operation._resolution.function
        self._add_operation_internal(method, path, operation)

    def _add_operation_internal(self, method: str, path: str, operation: AbstractOperation) -> None:
        self.router.add_route(path, operation.function, methods=[method])

    @staticmethod
    def make_security_handler_factory(pass_context_arg_name):
        """ Create default SecurityHandlerFactory to create all security check handlers """
        return MiddlewareSecurityHandlerFactory(pass_context_arg_name)
