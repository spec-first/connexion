"""
This module defines functionality specific to the Flask framework.
"""
import functools
import random
import re
import string
import typing as t

import flask
import werkzeug.routing

from connexion import jsonifier
from connexion.frameworks.abstract import Framework
from connexion.lifecycle import WSGIRequest
from connexion.uri_parsing import AbstractURIParser


class Flask(Framework):
    @staticmethod
    def is_framework_response(response: t.Any) -> bool:
        return isinstance(response, flask.Response) or isinstance(
            response, werkzeug.wrappers.Response
        )

    @classmethod
    def connexion_to_framework_response(cls, response):
        return cls.build_response(
            content_type=response.content_type,
            headers=response.headers,
            status_code=response.status_code,
            data=response.body,
        )

    @classmethod
    def build_response(
        cls,
        data: t.Any,
        *,
        content_type: str = None,
        headers: dict = None,
        status_code: int = None
    ):
        if cls.is_framework_response(data):
            return flask.current_app.make_response((data, status_code, headers))

        kwargs = {
            "mimetype": content_type,
            "headers": headers,
            "response": data,
            "status": status_code,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return flask.current_app.response_class(**kwargs)

    @staticmethod
    def get_request(*, uri_parser: AbstractURIParser, **kwargs) -> WSGIRequest:  # type: ignore
        return WSGIRequest(
            flask.request, uri_parser=uri_parser, view_args=flask.request.view_args
        )


PATH_PARAMETER = re.compile(r"\{([^}]*)\}")

# map Swagger type to flask path converter
# see http://flask.pocoo.org/docs/0.10/api/#url-route-registrations
PATH_PARAMETER_CONVERTERS = {"integer": "int", "number": "float", "path": "path"}


def flaskify_endpoint(identifier, randomize=None):
    """
    Converts the provided identifier in a valid flask endpoint name

    :type identifier: str
    :param randomize: If specified, add this many random characters (upper case
        and digits) to the endpoint name, separated by a pipe character.
    :type randomize: int | None
    :rtype: str

    """
    result = identifier.replace(".", "_")
    if randomize is None:
        return result

    chars = string.ascii_uppercase + string.digits
    return "{result}|{random_string}".format(
        result=result,
        random_string="".join(
            random.SystemRandom().choice(chars) for _ in range(randomize)
        ),
    )


def convert_path_parameter(match, types):
    name = match.group(1)
    swagger_type = types.get(name)
    converter = PATH_PARAMETER_CONVERTERS.get(swagger_type)
    return "<{}{}{}>".format(
        converter or "", ":" if converter else "", name.replace("-", "_")
    )


def flaskify_path(swagger_path, types=None):
    """
    Convert swagger path templates to flask path templates

    :type swagger_path: str
    :type types: dict
    :rtype: str

    >>> flaskify_path('/foo-bar/{my-param}')
    '/foo-bar/<my_param>'

    >>> flaskify_path('/foo/{someint}', {'someint': 'int'})
    '/foo/<int:someint>'
    """
    if types is None:
        types = {}
    convert_match = functools.partial(convert_path_parameter, types=types)
    return PATH_PARAMETER.sub(convert_match, swagger_path)


class FlaskJSONProvider(flask.json.provider.DefaultJSONProvider):
    """Custom JSONProvider which adds connexion defaults on top of Flask's"""

    @jsonifier.wrap_default
    def default(self, o):
        return super().default(o)


class NumberConverter(werkzeug.routing.BaseConverter):
    """Flask converter for OpenAPI number type"""

    regex = r"[+-]?[0-9]*(?:\.[0-9]*)?"

    def to_python(self, value):
        return float(value)


class IntegerConverter(werkzeug.routing.BaseConverter):
    """Flask converter for OpenAPI integer type"""

    regex = r"[+-]?[0-9]+"

    def to_python(self, value):
        return int(value)
