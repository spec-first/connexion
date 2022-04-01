from unittest.mock import MagicMock

import flask
import pytest

from especifico.apis.flask_api import FlaskApi
from especifico.decorators.validation import ParameterValidator
from especifico.exceptions import BadRequestProblem


def test_parameter_validator(monkeypatch):
    request = MagicMock(name="request")
    request.args = {}
    request.headers = {}
    request.cookies = {}
    request.params = {}
    app = MagicMock(name="app")

    app.response_class = flask.Response
    monkeypatch.setattr("flask.request", request)
    monkeypatch.setattr("flask.current_app", app)

    def orig_handler(*args, **kwargs):
        return "OK"

    params = [
        {"name": "p1", "in": "path", "type": "integer", "required": True},
        {"name": "h1", "in": "header", "type": "string", "enum": ["a", "b"]},
        {"name": "c1", "in": "cookie", "type": "string", "enum": ["a", "b"]},
        {"name": "q1", "in": "query", "type": "integer", "maximum": 3},
        {
            "name": "a1",
            "in": "query",
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {"type": "integer", "minimum": 0},
        },
    ]
    validator = ParameterValidator(params, FlaskApi)
    handler = validator(orig_handler)

    kwargs = {"query": {}, "headers": {}, "cookies": {}}
    request = MagicMock(path_params={}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail == "Missing path parameter 'p1'"
    request = MagicMock(path_params={"p1": "123"}, **kwargs)
    assert handler(request) == "OK"
    request = MagicMock(path_params={"p1": ""}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail == "Wrong type, expected 'integer' for path parameter 'p1'"
    request = MagicMock(path_params={"p1": "foo"}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail == "Wrong type, expected 'integer' for path parameter 'p1'"
    request = MagicMock(path_params={"p1": "1.2"}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail == "Wrong type, expected 'integer' for path parameter 'p1'"

    request = MagicMock(path_params={"p1": 1}, query={"q1": "4"}, headers={})
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail.startswith("4 is greater than the maximum of 3")
    request = MagicMock(path_params={"p1": 1}, query={"q1": "3"}, headers={}, cookies={})
    assert handler(request) == "OK"

    request = MagicMock(path_params={"p1": 1}, query={"a1": ["1", "2"]}, headers={}, cookies={})
    assert handler(request) == "OK"
    request = MagicMock(path_params={"p1": 1}, query={"a1": ["1", "a"]}, headers={})
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail.startswith("'a' is not of type 'integer'")
    request = MagicMock(path_params={"p1": "123"}, query={}, headers={}, cookies={"c1": "b"})
    assert handler(request) == "OK"

    request = MagicMock(path_params={"p1": "123"}, query={}, headers={}, cookies={"c1": "x"})
    with pytest.raises(BadRequestProblem) as exc:
        assert handler(request)
    assert exc.value.detail.startswith("'x' is not one of ['a', 'b']")
    request = MagicMock(path_params={"p1": 1}, query={"a1": ["1", "-1"]}, headers={})
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail.startswith("-1 is less than the minimum of 0")
    request = MagicMock(path_params={"p1": 1}, query={"a1": ["1"]}, headers={})
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail.startswith("[1] is too short")
    request = MagicMock(path_params={"p1": 1}, query={"a1": ["1", "2", "3", "4"]}, headers={})
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail.startswith("[1, 2, 3, 4] is too long")

    request = MagicMock(path_params={"p1": "123"}, query={}, headers={"h1": "a"}, cookies={})
    assert handler(request) == "OK"

    request = MagicMock(path_params={"p1": "123"}, query={}, headers={"h1": "x"})
    with pytest.raises(BadRequestProblem) as exc:
        handler(request)
    assert exc.value.detail.startswith("'x' is not one of ['a', 'b']")
