import functools
import re
import typing as t

import starlette.convertors
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import Response as StarletteResponse
from starlette.types import Receive, Scope

from connexion.frameworks.abstract import Framework
from connexion.lifecycle import ConnexionRequest
from connexion.uri_parsing import AbstractURIParser


class Starlette(Framework):
    @staticmethod
    def is_framework_response(response: t.Any) -> bool:
        return isinstance(response, StarletteResponse)

    @classmethod
    def connexion_to_framework_response(cls, response):
        return cls.build_response(
            status_code=response.status_code,
            content_type=response.content_type,
            headers=response.headers,
            data=response.body,
        )

    @classmethod
    def build_response(
        cls,
        data: t.Any,
        *,
        content_type: str = None,
        headers: dict = None,
        status_code: int = None,
    ):
        if isinstance(data, dict) or isinstance(data, list):
            response_cls = StarletteJSONResponse
        else:
            response_cls = StarletteResponse

        return response_cls(
            content=data,
            status_code=status_code,
            media_type=content_type,
            headers=headers,
        )

    @staticmethod
    def get_request(*, scope: Scope, receive: Receive, uri_parser: AbstractURIParser, **kwargs) -> ConnexionRequest:  # type: ignore
        return ConnexionRequest(scope, receive, uri_parser=uri_parser)


PATH_PARAMETER = re.compile(r"\{([^}]*)\}")
PATH_PARAMETER_CONVERTERS = {"integer": "int", "number": "float", "path": "path"}


def convert_path_parameter(match, types):
    name = match.group(1)
    swagger_type = types.get(name)
    converter = PATH_PARAMETER_CONVERTERS.get(swagger_type)
    return f'{{{name.replace("-", "_")}{":" if converter else ""}{converter or ""}}}'


def starlettify_path(swagger_path, types=None):
    """
    Convert swagger path templates to flask path templates

    :type swagger_path: str
    :type types: dict
    :rtype: str

    >>> starlettify_path('/foo-bar/{my-param}')
    '/foo-bar/{my_param}'

    >>> starlettify_path('/foo/{someint}', {'someint': 'int'})
    '/foo/{someint:int}'
    """
    if types is None:
        types = {}
    convert_match = functools.partial(convert_path_parameter, types=types)
    return PATH_PARAMETER.sub(convert_match, swagger_path)


class FloatConverter(starlette.convertors.FloatConvertor):
    """Starlette converter for OpenAPI number type"""

    regex = r"[+-]?[0-9]*(\.[0-9]*)?"


class IntegerConverter(starlette.convertors.IntegerConvertor):
    """Starlette converter for OpenAPI integer type"""

    regex = r"[+-]?[0-9]+"
