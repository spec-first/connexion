"""
This module defines Exception classes used by Connexion to generate a proper response.
"""

import typing as t

from jsonschema.exceptions import ValidationError
from starlette.exceptions import HTTPException

from .problem import problem


class ConnexionException(Exception):
    pass


class ResolverError(LookupError, ConnexionException):
    pass


class InvalidSpecification(ValidationError, ConnexionException):
    pass


class MissingMiddleware(ConnexionException):
    pass


# HTTP ERRORS


class ProblemException(HTTPException, ConnexionException):
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
        """
        This exception holds arguments that are going to be passed to the
        `connexion.problem` function to generate a proper response.
        """
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


class ClientError(ProblemException):
    def __init__(self, status: int = 400, title: str = None, *, detail: str = None):
        super().__init__(status=status, title=title, detail=detail)


class BadRequestProblem(ClientError):
    def __init__(self, detail=None):
        super().__init__(status=400, title="Bad Request", detail=detail)


class ExtraParameterProblem(BadRequestProblem):
    def __init__(self, *, param_type: str, extra_params: t.Iterable[str]):
        detail = f"Extra {param_type} parameter(s) {','.join(extra_params)} not in spec"
        super().__init__(detail=detail)


class TypeValidationError(BadRequestProblem):
    def __init__(self, schema_type: str, parameter_type: str, parameter_name: str):
        """Exception raised when type validation fails"""
        detail = f"Wrong type, expected '{schema_type}' for {parameter_type} parameter '{parameter_name}'"
        super().__init__(detail=detail)


class Unauthorized(ClientError):

    description = (
        "The server could not verify that you are authorized to access"
        " the URL requested. You either supplied the wrong credentials"
        " (e.g. a bad password), or your browser doesn't understand"
        " how to supply the credentials required."
    )

    def __init__(self, detail: str = description):
        super().__init__(401, title="Unauthorized", detail=detail)


class OAuthProblem(Unauthorized):
    pass


class OAuthResponseProblem(OAuthProblem):
    pass


class Forbidden(HTTPException):
    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = (
                "You don't have the permission to access the requested"
                " resource. It is either read-protected or not readable by the"
                " server."
            )
        super().__init__(403, detail=detail)


class OAuthScopeProblem(Forbidden):
    def __init__(self, token_scopes: list, required_scopes: list) -> None:
        self.required_scopes = required_scopes
        self.token_scopes = token_scopes
        detail = (
            f"Provided token does not have the required scopes. "
            f"Provided: {token_scopes}; Required: {required_scopes}"
        )
        super().__init__(detail=detail)


class UnsupportedMediaTypeProblem(ClientError):
    def __init__(self, detail: t.Optional[str] = None):
        super().__init__(status=415, title="Unsupported Media Type", detail=detail)


# SERVER ERRORS (5XX)


class ServerError(ProblemException):
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
    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = (
                "The server encountered an internal error and was unable to complete your "
                "request. Either the server is overloaded or there is an error in the application."
            )
        super().__init__(status=500, title="Internal Server Error", detail=detail)


class NonConformingResponse(InternalServerError):
    def __init__(self, detail: t.Optional[str] = None):
        super().__init__(detail=detail)


class NonConformingResponseBody(NonConformingResponse):
    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = "Response body does not conform to specification"

        super().__init__(detail=detail)


class NonConformingResponseHeaders(NonConformingResponse):
    def __init__(self, detail: t.Optional[str] = None):
        if detail is None:
            detail = "Response headers do not conform to specification"

        super().__init__(detail=detail)


class ResolverProblem(ServerError):
    def __init__(self, status: int = 501, *, detail: t.Optional[str] = None):
        super().__init__(status=status, title="Not Implemented", detail=detail)
