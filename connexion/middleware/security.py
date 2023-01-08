import logging
import typing as t
from collections import defaultdict

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.exceptions import ProblemException
from connexion.lifecycle import MiddlewareRequest
from connexion.middleware.abstract import RoutedAPI, RoutedMiddleware
from connexion.operations import AbstractOperation
from connexion.security import SecurityHandlerFactory

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
        operation: AbstractOperation,
        *,
        next_app: ASGIApp,
        security_handler_factory: SecurityHandlerFactory,
    ) -> "SecurityOperation":
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
                auth_funcs.append(self.security_handler_factory.verify_none())
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
                    token_info_func = self.security_handler_factory.get_tokeninfo_func(
                        security_scheme
                    )
                    scope_validate_func = (
                        self.security_handler_factory.get_scope_validate_func(
                            security_scheme
                        )
                    )
                    if not token_info_func:
                        logger.warning("... x-tokenInfoFunc missing", extra=vars(self))
                        break

                    sec_req_funcs[
                        scheme_name
                    ] = self.security_handler_factory.verify_oauth(
                        token_info_func, scope_validate_func, required_scopes
                    )

                # Swagger 2.0
                elif security_scheme["type"] == "basic":
                    basic_info_func = self.security_handler_factory.get_basicinfo_func(
                        security_scheme
                    )
                    if not basic_info_func:
                        logger.warning("... x-basicInfoFunc missing", extra=vars(self))
                        break

                    sec_req_funcs[
                        scheme_name
                    ] = self.security_handler_factory.verify_basic(basic_info_func)

                # OpenAPI 3.0.0
                elif security_scheme["type"] == "http":
                    scheme = security_scheme["scheme"].lower()
                    if scheme == "basic":
                        basic_info_func = (
                            self.security_handler_factory.get_basicinfo_func(
                                security_scheme
                            )
                        )
                        if not basic_info_func:
                            logger.warning(
                                "... x-basicInfoFunc missing", extra=vars(self)
                            )
                            break

                        sec_req_funcs[
                            scheme_name
                        ] = self.security_handler_factory.verify_basic(basic_info_func)
                    elif scheme == "bearer":
                        bearer_info_func = (
                            self.security_handler_factory.get_bearerinfo_func(
                                security_scheme
                            )
                        )
                        if not bearer_info_func:
                            logger.warning(
                                "... x-bearerInfoFunc missing", extra=vars(self)
                            )
                            break
                        sec_req_funcs[
                            scheme_name
                        ] = self.security_handler_factory.verify_bearer(
                            bearer_info_func
                        )
                    else:
                        logger.warning(
                            "... Unsupported http authorization scheme %s" % scheme,
                            extra=vars(self),
                        )
                        break

                elif security_scheme["type"] == "apiKey":
                    scheme = security_scheme.get("x-authentication-scheme", "").lower()
                    if scheme == "bearer":
                        bearer_info_func = (
                            self.security_handler_factory.get_bearerinfo_func(
                                security_scheme
                            )
                        )
                        if not bearer_info_func:
                            logger.warning(
                                "... x-bearerInfoFunc missing", extra=vars(self)
                            )
                            break
                        sec_req_funcs[
                            scheme_name
                        ] = self.security_handler_factory.verify_bearer(
                            bearer_info_func
                        )
                    else:
                        apikey_info_func = (
                            self.security_handler_factory.get_apikeyinfo_func(
                                security_scheme
                            )
                        )
                        if not apikey_info_func:
                            logger.warning(
                                "... x-apikeyInfoFunc missing", extra=vars(self)
                            )
                            break

                        sec_req_funcs[
                            scheme_name
                        ] = self.security_handler_factory.verify_api_key(
                            apikey_info_func,
                            security_scheme["in"],
                            security_scheme["name"],
                        )

                else:
                    logger.warning(
                        "... Unsupported security scheme type %s"
                        % security_scheme["type"],
                        extra=vars(self),
                    )
                    break
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
        request = MiddlewareRequest(scope)
        await self.verification_fn(request)
        await self.next_app(scope, receive, send)


class SecurityAPI(RoutedAPI[SecurityOperation]):
    def __init__(self, *args, auth_all_paths: bool = False, **kwargs):
        super().__init__(*args, **kwargs)

        self.security_handler_factory = SecurityHandlerFactory()

        if auth_all_paths:
            self.add_auth_on_not_found()
        else:
            self.operations: t.MutableMapping[str, SecurityOperation] = {}

        self.add_paths()

    def add_auth_on_not_found(self) -> None:
        """Register a default SecurityOperation for routes that are not found."""
        default_operation = self.make_operation(self.specification)
        self.operations = defaultdict(lambda: default_operation)

    def make_operation(self, operation: AbstractOperation) -> SecurityOperation:
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
