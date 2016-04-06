import json

from connexion.decorators.validation import ParameterValidator
# we are using "mock" module here for Py 2.7 support
from mock import MagicMock


def test_parameter_validator(monkeypatch):
    request = MagicMock(name='request')
    request.args = {}
    request.headers = {}
    request.params = {}
    app = MagicMock(name='app')
    app.response_class = lambda a, mimetype, status: json.loads(''.join(a))['detail']
    monkeypatch.setattr('flask.request', request)
    monkeypatch.setattr('flask.current_app', app)

    def orig_handler(*args, **kwargs):
        return 'OK'

    params = [{'name': 'p1', 'in': 'path', 'type': 'integer', 'required': True},
              {'name': 'h1', 'in': 'header', 'type': 'string', 'enum': ['a', 'b']},
              {'name': 'q1', 'in': 'query', 'type': 'integer', 'maximum': 3},
              {'name': 'a1', 'in': 'query', 'type': 'array', 'items': {'type': 'integer', 'minimum': 0}}]
    validator = ParameterValidator(params)
    handler = validator(orig_handler)

    assert handler() == "Missing path parameter 'p1'"
    assert handler(p1='123') == 'OK'
    assert handler(p1='') == "Wrong type, expected 'integer' for path parameter 'p1'"
    assert handler(p1='foo') == "Wrong type, expected 'integer' for path parameter 'p1'"
    assert handler(p1='1.2') == "Wrong type, expected 'integer' for path parameter 'p1'"

    request.args = {'q1': '4'}
    assert handler(p1=1).startswith('4 is greater than the maximum of 3')
    request.args = {'q1': '3'}
    assert handler(p1=1) == 'OK'

    request.args = {'a1': "1,2"}
    assert handler(p1=1) == "OK"
    request.args = {'a1': "1,a"}
    assert handler(p1=1).startswith("'a' is not of type 'integer'")
    request.args = {'a1': "1,-1"}
    assert handler(p1=1).startswith("-1 is less than the minimum of 0")
    del request.args['a1']

    request.headers = {'h1': 'a'}
    assert handler(p1='123') == 'OK'

    request.headers = {'h1': 'x'}
    assert handler(p1='123').startswith("'x' is not one of ['a', 'b']")
