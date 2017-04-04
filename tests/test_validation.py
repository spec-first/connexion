import json

import flask
from connexion.apis.flask_api import FlaskApi
from connexion.decorators.validation import ParameterValidator
# we are using "mock" module here for Py 2.7 support
from mock import MagicMock


def test_parameter_validator(monkeypatch):
    request = MagicMock(name='request')
    request.args = {}
    request.headers = {}
    request.params = {}
    app = MagicMock(name='app')

    app.response_class = flask.Response
    monkeypatch.setattr('flask.request', request)
    monkeypatch.setattr('flask.current_app', app)

    def orig_handler(*args, **kwargs):
        return 'OK'

    params = [{'name': 'p1', 'in': 'path', 'type': 'integer', 'required': True},
              {'name': 'h1', 'in': 'header', 'type': 'string', 'enum': ['a', 'b']},
              {'name': 'q1', 'in': 'query', 'type': 'integer', 'maximum': 3},
              {'name': 'a1', 'in': 'query', 'type': 'array', 'minItems': 2, 'maxItems': 3,
               'items': {'type': 'integer', 'minimum': 0}}]
    validator = ParameterValidator(params, FlaskApi)
    handler = validator(orig_handler)

    kwargs = {'query': {}, 'headers': {}}
    request = MagicMock(path_params={}, **kwargs)
    assert json.loads(handler(request).data.decode())['detail'] == "Missing path parameter 'p1'"
    request = MagicMock(path_params={'p1': '123'}, **kwargs)
    assert handler(request) == 'OK'
    request = MagicMock(path_params={'p1': ''}, **kwargs)
    assert json.loads(handler(request).data.decode())['detail'] == "Wrong type, expected 'integer' for path parameter 'p1'"
    request = MagicMock(path_params={'p1': 'foo'}, **kwargs)
    assert json.loads(handler(request).data.decode())['detail'] == "Wrong type, expected 'integer' for path parameter 'p1'"
    request = MagicMock(path_params={'p1': '1.2'}, **kwargs)
    assert json.loads(handler(request).data.decode())['detail'] == "Wrong type, expected 'integer' for path parameter 'p1'"

    request = MagicMock(path_params={'p1': 1}, query={'q1': '4'}, headers={})
    assert json.loads(handler(request).data.decode())['detail'].startswith('4 is greater than the maximum of 3')
    request = MagicMock(path_params={'p1': 1}, query={'q1': '3'}, headers={})
    assert handler(request) == 'OK'

    request = MagicMock(path_params={'p1': 1}, query={'a1': "1,2"}, headers={})
    assert handler(request) == "OK"
    request = MagicMock(path_params={'p1': 1}, query={'a1': "1,a"}, headers={})
    assert json.loads(handler(request).data.decode())['detail'].startswith("'a' is not of type 'integer'")
    request = MagicMock(path_params={'p1': 1}, query={'a1': "1,-1"}, headers={})
    assert json.loads(handler(request).data.decode())['detail'].startswith("-1 is less than the minimum of 0")
    request = MagicMock(path_params={'p1': 1}, query={'a1': "1"}, headers={})
    assert json.loads(handler(request).data.decode())['detail'].startswith("[1] is too short")
    request = MagicMock(path_params={'p1': 1}, query={'a1': "1,2,3,4"}, headers={})
    assert json.loads(handler(request).data.decode())['detail'].startswith("[1, 2, 3, 4] is too long")

    request = MagicMock(path_params={'p1': '123'}, query={}, headers={'h1': 'a'})
    assert handler(request) == 'OK'

    request = MagicMock(path_params={'p1': '123'}, query={}, headers={'h1': 'x'})
    assert json.loads(handler(request).data.decode())['detail'].startswith("'x' is not one of ['a', 'b']")
