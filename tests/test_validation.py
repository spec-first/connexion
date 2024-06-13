from unittest.mock import MagicMock
from urllib.parse import quote_plus

import pytest
from connexion.exceptions import BadRequestProblem
from connexion.lifecycle import ConnexionRequest
from connexion.uri_parsing import Swagger2URIParser
from connexion.validators import AbstractRequestBodyValidator, ParameterValidator
from starlette.datastructures import QueryParams


def test_parameter_validator(monkeypatch):
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

    uri_parser = Swagger2URIParser(params, {})
    validator = ParameterValidator(params, uri_parser=uri_parser)

    kwargs = {"query_params": {}, "headers": {}, "cookies": {}}
    request = MagicMock(path_params={}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail == "Missing path parameter 'p1'"

    request = MagicMock(path_params={"p1": "123"}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("'123' is not of type 'integer'")

    request = MagicMock(path_params={"p1": ""}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("'' is not of type 'integer'")

    request = MagicMock(path_params={"p1": "foo"}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("'foo' is not of type 'integer'")

    request = MagicMock(path_params={"p1": "1.2"}, **kwargs)
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("'1.2' is not of type 'integer'")

    request = MagicMock(
        path_params={"p1": 1}, query_params={"q1": 4}, headers={}, cookies={}
    )
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("4 is greater than the maximum of 3")

    request = MagicMock(
        path_params={"p1": 1}, query_params={"q1": 3}, headers={}, cookies={}
    )
    try:
        validator.validate_request(request)
    except Exception as e:
        pytest.fail(str(e))

    request = MagicMock(
        path_params={"p1": 1}, query_params={"a1": [1, 2]}, headers={}, cookies={}
    )
    try:
        validator.validate_request(request)
    except Exception as e:
        pytest.fail(str(e))

    request = MagicMock(
        path_params={"p1": 1}, query_params={"a1": [1, "a"]}, headers={}, cookies={}
    )
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("'a' is not of type 'integer'")

    request = MagicMock(
        path_params={"p1": 123}, query_params={}, headers={}, cookies={"c1": "b"}
    )
    try:
        validator.validate_request(request)
    except Exception as e:
        pytest.fail(str(e))

    request = MagicMock(
        path_params={"p1": 123}, query={}, headers={}, cookies={"c1": "x"}
    )
    with pytest.raises(BadRequestProblem) as exc:
        assert validator.validate_request(request)
        assert exc.value.detail.startswith("'x' is not one of ['a', 'b']")

    request = MagicMock(
        path_params={"p1": 1}, query_params={"a1": [1, -1]}, headers={}, cookies={}
    )
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("-1 is less than the minimum of 0")

    request = MagicMock(
        path_params={"p1": 1}, query_params={"a1": 1}, headers={}, cookies={}
    )
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("[1] is too short")

    request = MagicMock(
        path_params={"p1": 1}, query_params={"a1": [1, 2, 3, 4]}, headers={}, cookies={}
    )
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("[1, 2, 3, 4] is too long")

    request = MagicMock(
        path_params={"p1": 123}, query_params={}, headers={"h1": "a"}, cookies={}
    )
    try:
        validator.validate_request(request)
    except Exception as e:
        pytest.fail(str(e))

    request = MagicMock(
        path_params={"p1": 123}, query_params={}, headers={"h1": "x"}, cookies={}
    )
    with pytest.raises(BadRequestProblem) as exc:
        validator.validate_request(request)
        assert exc.value.detail.startswith("'x' is not one of ['a', 'b']")


async def test_stream_replay():
    messages = [
        {"body": b"message 1", "more_body": True},
        {"body": b"message 2", "more_body": False},
    ]

    async def receive():
        return b""

    wrapped_receive = AbstractRequestBodyValidator._insert_messages(
        receive, messages=messages
    )

    replay = []
    more_body = True
    while more_body:
        message = await wrapped_receive()
        replay.append(message)
        more_body = message.get("more_body", False)

        assert len(replay) <= len(
            messages
        ), "Replayed more messages than received, break out of while loop"

    assert messages == replay
