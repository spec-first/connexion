import logging
import typing as t
from collections import defaultdict

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import ProblemException
from connexion.lifecycle import ConnexionRequest
from connexion.middleware.abstract import RoutedAPI, RoutedMiddleware
from connexion.operations import AbstractOperation
from connexion.security import SecurityHandlerFactory
from connexion.spec import Specification

logger = logging.getLogger("connexion.middleware.security")


class SecurityOperation:
    def __init__(
        self,
        next_app: ASGIApp,
        *,
        security_handler_factory: SecurityHandlerFactory,
        security: list,
        security_schemes: dict,
    ):
        self.next_app = next_app
        self.security_handler_factory = security_handler_factory
        self.security = security
        self.security_schemes = security_schemes
        self.verification_fn = self._get_verification_fn()

    @classmethod
    def from_operation(
        cls,
        operation: t.Union[AbstractOperation, Specification],
        *,
        next_app: ASGIApp,
        security_handler_factory: SecurityHandlerFactory,
    ) -> "SecurityOperation":
        """Create a SecurityOperation from an Operation of Specification instance

        :param operation: The operation can be both an Operation or Specification instance here
            since security is defined at both levels in the OpenAPI spec. Creating a
            SecurityOperation based on a Specification can be used to create a SecurityOperation
            for routes not explicitly defined in the specification.
        :param next_app: The next ASGI app to call.
        :param security_handler_factory: The factory to be used to generate security handlers for
            the different security schemes.
        """
        return cls(
            next_app=next_app,
            security_handler_factory=security_handler_factory,
            security=operation.security,
            security_schemes=operation.security_schemes,
        )

    def _get_verification_fn(self):
        logger.debug("... Security: %s", self.security, extra=vars(self))
        if not self.security:
            return self.security_handler_factory.security_passthrough

        auth_funcs = []
        for security_req in self.security:
            if not security_req:
                auth_funcs.append(self.security_handler_factory.verify_none)
                continue

            sec_req_funcs = {}
            oauth = False
            for scheme_name, required_scopes in security_req.items():
                security_scheme = self.security_schemes[scheme_name]

                if security_scheme["type"] == "oauth2":
                    if oauth:
                        logger.warning(
                            "... multiple OAuth2 security schemes in AND fashion not supported",
                            extra=vars(self),
                        )
                        break
                    oauth = True

                sec_req_func = self.security_handler_factory.parse_security_scheme(
                    security_scheme, required_scopes
                )
                if sec_req_func is None:
                    break

                sec_req_funcs[scheme_name] = sec_req_func

            else:
                # No break encountered: no missing funcs
                if len(sec_req_funcs) == 1:
                    (func,) = sec_req_funcs.values()
                    auth_funcs.append(func)
                else:
                    auth_funcs.append(
                        self.security_handler_factory.verify_multiple_schemes(
                            sec_req_funcs
                        )
                    )

        return self.security_handler_factory.verify_security(auth_funcs)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.security:
            await self.next_app(scope, receive, send)
            return

        request = ConnexionRequest(scope)
        await self.verification_fn(request)
        await self.next_app(scope, receive, send)


class SecurityAPI(RoutedAPI[SecurityOperation]):
    def __init__(
        self, *args, auth_all_paths: bool = False, security_map: dict = None, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.security_handler_factory = SecurityHandlerFactory(security_map)

        if auth_all_paths:
            self.add_auth_on_not_found()
        else:
            self.operations: t.MutableMapping[t.Optional[str], SecurityOperation] = {}

        self.add_paths()

    def add_auth_on_not_found(self) -> None:
        """Register a default SecurityOperation for routes that are not found."""
        default_operation = self.make_operation(self.specification)
        self.operations = defaultdict(lambda: default_operation)

    def make_operation(
        self, operation: t.Union[AbstractOperation, Specification]
    ) -> SecurityOperation:
        """Create a SecurityOperation from an Operation of Specification instance

        :param operation: The operation can be both an Operation or Specification instance here
            since security is defined at both levels in the OpenAPI spec. Creating a
            SecurityOperation based on a Specification can be used to create a SecurityOperation
            for routes not explicitly defined in the specification.
        """
        return SecurityOperation.from_operation(
            operation,
            next_app=self.next_app,
            security_handler_factory=self.security_handler_factory,
        )


class SecurityMiddleware(RoutedMiddleware[SecurityAPI]):
    """Middleware to check if operation is accessible on scope."""

    api_cls = SecurityAPI


class MissingSecurityOperation(ProblemException):
    pass
