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

    def _response_class(data, mimetype, content_type, headers):
        response = MagicMock(name='response')
        response.detail = json.loads(''.join(data))['detail']
        response.headers = MagicMock()
        return response

    app.response_class = _response_class
    monkeypatch.setattr('flask.request', request)
    monkeypatch.setattr('flask.current_app', app)

    def orig_handler(*args, **kwargs):
        return 'OK'

    params = [{'name': 'p1', 'in': 'path', 'type': 'integer', 'required': True},
              {'name': 'h1', 'in': 'header', 'type': 'string', 'enum': ['a', 'b']},
              {'name': 'q1', 'in': 'query', 'type': 'integer', 'maximum': 3},
              {'name': 'a1', 'in': 'query', 'type': 'array', 'minItems': 2, 'maxItems': 3,
               'items': {'type': 'integer', 'minimum': 0}}]
    validator = ParameterValidator(params)
    handler = validator(orig_handler)

    assert handler().flask_response_object().detail == "Missing path parameter 'p1'"
    assert handler(p1='123') == 'OK'
    assert handler(p1='').flask_response_object().detail == "Wrong type, expected 'integer' for path parameter 'p1'"
    assert handler(p1='foo').flask_response_object().detail == "Wrong type, expected 'integer' for path parameter 'p1'"
    assert handler(p1='1.2').flask_response_object().detail == "Wrong type, expected 'integer' for path parameter 'p1'"

    request.args = {'q1': '4'}
    assert handler(p1=1).flask_response_object().detail.startswith('4 is greater than the maximum of 3')
    request.args = {'q1': '3'}
    assert handler(p1=1) == 'OK'

    request.args = {'a1': "1,2"}
    assert handler(p1=1) == "OK"
    request.args = {'a1': "1,a"}
    assert handler(p1=1).flask_response_object().detail.startswith("'a' is not of type 'integer'")
    request.args = {'a1': "1,-1"}
    assert handler(p1=1).flask_response_object().detail.startswith("-1 is less than the minimum of 0")
    request.args = {'a1': "1"}
    assert handler(p1=1).flask_response_object().detail.startswith("[1] is too short")
    request.args = {'a1': "1,2,3,4"}
    assert handler(p1=1).flask_response_object().detail.startswith("[1, 2, 3, 4] is too long")
    del request.args['a1']

    request.headers = {'h1': 'a'}
    assert handler(p1='123') == 'OK'

    request.headers = {'h1': 'x'}
    assert handler(p1='123').flask_response_object().detail.startswith("'x' is not one of ['a', 'b']")
