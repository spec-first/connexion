import logging
import pathlib
import typing as t
from collections import defaultdict

from starlette.types import ASGIApp, Receive, Scope, Send

from connexion.apis.abstract import AbstractSpecAPI
from connexion.exceptions import MissingMiddleware, ProblemException
from connexion.http_facts import METHODS
from connexion.lifecycle import MiddlewareRequest
from connexion.middleware import AppMiddleware
from connexion.middleware.routing import ROUTING_CONTEXT
from connexion.operations import AbstractOperation
from connexion.resolver import ResolverError
from connexion.security import SecurityHandlerFactory
from connexion.spec import Specification

logger = logging.getLogger("connexion.middleware.security")


class SecurityMiddleware(AppMiddleware):
    """Middleware to check if operation is accessible on scope."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.apis: t.Dict[str, SecurityAPI] = {}

    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        api = SecurityAPI(specification, **kwargs)
        self.apis[api.base_path] = api

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
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
                operation = api.operations[operation_id]
            except KeyError as e:
                if operation_id is None:
                    logger.debug(
                        "Skipping security check for operation without id. Enable "
                        "`auth_all_paths` to check security for unknown operations."
                    )
                else:
                    raise MissingSecurityOperation(
                        "Encountered unknown operation_id."
                    ) from e

            else:
                request = MiddlewareRequest(scope)
                await operation(request)

        await self.app(scope, receive, send)


class SecurityAPI(AbstractSpecAPI):
    def __init__(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        auth_all_paths: bool = False,
        *args,
        **kwargs
    ):
        super().__init__(specification, *args, **kwargs)
        self.security_handler_factory = SecurityHandlerFactory("context")

        if auth_all_paths:
            self.add_auth_on_not_found()
        else:
            self.operations: t.Dict[str, SecurityOperation] = {}

        self.add_paths()

    def add_auth_on_not_found(self):
        """Register a default SecurityOperation for routes that are not found."""
        default_operation = self.make_operation(self.specification)
        self.operations = defaultdict(lambda: default_operation)

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
        security_operation = self.make_operation(operation)
        self._add_operation_internal(operation.operation_id, security_operation)

    def make_operation(self, operation: t.Union[AbstractOperation, Specification]):
        return SecurityOperation.from_operation(
            operation,
            security_handler_factory=self.security_handler_factory,
        )

    def _add_operation_internal(
        self, operation_id: str, operation: "SecurityOperation"
    ):
        self.operations[operation_id] = operation


class SecurityOperation:
    def __init__(
        self,
        security_handler_factory: SecurityHandlerFactory,
        security: list,
        security_schemes: dict,
    ):
        self.security_handler_factory = security_handler_factory
        self.security = security
        self.security_schemes = security_schemes
        self.verification_fn = self._get_verification_fn()

    @classmethod
    def from_operation(
        cls,
        operation: t.Union[AbstractOperation, Specification],
        security_handler_factory: SecurityHandlerFactory,
    ):
        return cls(
            security_handler_factory,
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

    async def __call__(self, request: MiddlewareRequest):
        await self.verification_fn(request)


class MissingSecurityOperation(ProblemException):
    pass
