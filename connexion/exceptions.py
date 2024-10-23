"""
This module defines Exception classes used by Connexion to generate a proper response.
"""

import typing as t

from jsonschema.exceptions import ValidationError
from starlette.exceptions import HTTPException

from .problem import problem


class ConnexionException(Exception):
    """Base class for any exception thrown by the Connexion framework."""


class ResolverError(LookupError, ConnexionException):
    """Error raised at startup when the resolver cannot find a view function for an endpoint in
    your specification, and no ``resolver_error`` is configured."""


class InvalidSpecification(ValidationError, ConnexionException):
    """Error raised at startup when the provided specification cannot be validated."""


class MissingMiddleware(ConnexionException):
    """Error raised when you're leveraging behavior that depends on a specific middleware,
    and that middleware is not part of your middleware stack."""


# HTTP ERRORS


class ProblemException(HTTPException, ConnexionException):
    """
    This exception holds arguments that are going to be passed to the
    `connexion.problem` function to generate a proper response.
    """

    def __init__(
        self,
        *,
        status=500,
        title=None,
        detail=None,
        type=None,
        instance=None,
        headers=None,
        ext=None,
    ):
        self.status = self.status_code = status
        self.title = title
        self.detail = detail
        self.type = type
        self.instance = instance
        self.headers = headers
        self.ext = ext

    def to_problem(self):
        return problem(
            status=self.status,
            title=self.title,
            detail=self.detail,
            type=self.type,
            instance=self.instance,
            headers=self.headers,
            ext=self.ext,
        )


# CLIENT ERRORS (4XX)


class ClientProblem(ProblemException):
    """Base exception for any 4XX error. Returns 400 by default, however
    :class:`BadRequestProblem` should be preferred for 400 errors."""

    def __init__(
        self,
        status: int = 400,
        title: t.Optional[str] = None,
        *,
        detail: t.Optional[str] = None,
    ):
        super().__init__(status=status, title=title, detail=detail)


class BadRequestProblem(ClientProblem):
    """Problem class for 400 Bad Request errors."""

    def __init__(self, detail=None):
        super().__init__(status=400, title="Bad Request", detail=detail)


class ExtraParameterProblem(BadRequestProblem):
    """Problem class for 400 Bad Request errors raised when extra query or form parameters are
    detected and ``strict_validation`` is enabled."""

    def __init__(self, *, param_type: str, extra_params: t.Iterable[str]):
        detail = f"Extra {param_type} parameter(s) {','.join(extra_params)} not in spec"
        super().__init__(detail=detail)


class TypeValidationError(BadRequestProblem):
    """Problem class for 400 Bad Request errors raised when path, query or form parameters with
    an incorrect type are detected."""

    def __init__(self, schema_type: str, parameter_type: str, parameter_name: str):
        detail = f"Wrong type, expected '{schema_type}' for {parameter_type} parameter '{parameter_name}'"
        super().__init__(detail=detail)


class Unauthorized(ClientProblem):
    """Problem class for 401 Unauthorized errors."""

    description = (
        "The server could not verify that you are authorized to access"
        " the URL requested. You either supplied the wrong credentials"
        " (e.g. a bad password), or your browser doesn't understand"
        " how to supply the credentials required."
    )

    def __init__(self, detail: str = description):
        super().__init__(401, title="Unauthorized", detail=detail)


class OAuthProblem(Unauthorized):
    """Problem class for 401 Unauthorized errors raised when there is an issue with the received
    OAuth headers."""

    pass


class OAuthResponseProblem(OAuthProblem):
    """Problem class for 401 Unauthorized errors raised when improper OAuth credentials are
    retrieved from your OAuth server."""

    pass


class Forbidden(HTTPException):
    """Problem class for 403 Unauthorized errors."""

    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = (
                "You don't have the permission to access the requested"
                " resource. It is either read-protected or not readable by the"
                " server."
            )
        super().__init__(403, detail=detail)


class OAuthScopeProblem(Forbidden):
    """Problem class for 403 Unauthorized errors raised because of OAuth scope validation errors."""

    def __init__(self, token_scopes: list, required_scopes: list) -> None:
        self.required_scopes = required_scopes
        self.token_scopes = token_scopes
        detail = (
            f"Provided token does not have the required scopes. "
            f"Provided: {token_scopes}; Required: {required_scopes}"
        )
        super().__init__(detail=detail)


class UnsupportedMediaTypeProblem(ClientProblem):
    """Problem class for 415 Unsupported Media Type errors which are raised when Connexion
    receives a request with an unsupported media type header."""

    def __init__(self, detail: t.Optional[str] = None):
        super().__init__(status=415, title="Unsupported Media Type", detail=detail)


# SERVER ERRORS (5XX)


class ServerError(ProblemException):
    """Base exception for any 5XX error. Returns 500 by default, however
    :class:`InternalServerError` should be preferred for 500 errors."""

    def __init__(
        self,
        status: int = 500,
        title: t.Optional[str] = None,
        *,
        detail: t.Optional[str] = None,
    ):
        if title is None:
            title = "Internal Server Error"

        super().__init__(status=status, title=title, detail=detail)


class InternalServerError(ServerError):
    """Problem class for 500 Internal Server errors."""

    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = (
                "The server encountered an internal error and was unable to complete your "
                "request. Either the server is overloaded or there is an error in the application."
            )
        super().__init__(status=500, title="Internal Server Error", detail=detail)


class NonConformingResponse(InternalServerError):
    """Problem class for 500 Internal Server errors raised because of a returned response not
    matching the specification if response validation is enabled."""

    def __init__(self, detail: t.Optional[str] = None):
        super().__init__(detail=detail)


class NonConformingResponseBody(NonConformingResponse):
    """Problem class for 500 Internal Server errors raised because of a returned response body not
    matching the specification if response validation is enabled."""

    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = "Response body does not conform to specification"

        super().__init__(detail=detail)


class NonConformingResponseHeaders(NonConformingResponse):
    """Problem class for 500 Internal Server errors raised because of a returned response headers
    not matching the specification if response validation is enabled."""

    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = "Response headers do not conform to specification"

        super().__init__(detail=detail)


class ResolverProblem(ServerError):
    """Problem class for 501 Not Implemented errors raised when the resolver cannot find a view
    function to handle the incoming request."""

    def __init__(self, status: int = 501, *, detail: t.Optional[str] = None):
        super().__init__(status=status, title="Not Implemented", detail=detail)
