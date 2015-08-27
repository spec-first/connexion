import flask
import json
import pytest
from unittest.mock import MagicMock

from connexion.problem import problem
from connexion.decorators.validation import validate_pattern, validate_minimum, validate_maximum, ParameterValidator

def test_validate_pattern():
    assert validate_pattern({}, '') is None
    assert validate_pattern({'pattern': 'a'}, 'a') is None
    assert validate_pattern({'pattern': 'a'}, 'b') == 'Invalid value, pattern "a" does not match'


def test_validate_minimum():
    assert validate_minimum({}, 1) is None
    assert validate_minimum({'minimum': 1}, 1) is None
    assert validate_minimum({'minimum': 1.1}, 1) == 'Invalid value, must be at least 1.1'


def test_validate_maximum():
    assert validate_maximum({}, 1) is None
    assert validate_maximum({'maximum': 1}, 1) is None
    assert validate_maximum({'maximum': 0}, 1) == 'Invalid value, must be at most 0'


def test_parameter_validator(monkeypatch):

    request = MagicMock(name='request')
    app = MagicMock(name='app')
    app.response_class = lambda a, mimetype, status: json.loads(a)['detail']
    monkeypatch.setattr('flask.request', request)
    monkeypatch.setattr('flask.current_app', app)

    def orig_handler(*args, **kwargs):
        return 'OK'

    params = [{'name': 'p1', 'in': 'path', 'type': 'integer'}]
    validator = ParameterValidator(params)
    handler = validator(orig_handler)

    assert handler() == "Missing path parameter 'p1'"
    assert handler(p1='123') == 'OK'
    assert handler(p1='') == "Wrong type, expected 'integer' for path parameter 'p1'"
    assert handler(p1='foo') == "Wrong type, expected 'integer' for path parameter 'p1'"
    assert handler(p1='1.2') == "Wrong type, expected 'integer' for path parameter 'p1'"
