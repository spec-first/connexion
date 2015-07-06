import flask
import functools
import types

from flask import abort


def validate_schema(data, schema):
    _type = schema.get('type')
    if _type == 'array':
        if not isinstance(data, list):
            raise abort(400)
        for item in data:
            validate_schema(item, schema.get('items'))

    if _type == 'object':
        if not isinstance(data, dict):
            raise abort(400)
        for required_key in schema.get('required', []):
            if required_key not in data:
                raise abort(400)


class RequestBodyValidator:

    def __init__(self, schema):
        self.schema = schema

    def __call__(self, function: types.FunctionType) -> types.FunctionType:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = flask.request.json
            validate_schema(data, self.schema)
            response = function(*args, **kwargs)
            return response

        return wrapper
