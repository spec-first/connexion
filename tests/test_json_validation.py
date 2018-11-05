import json

from jsonschema.validators import _utils, extend

import pytest
from conftest import build_app_from_fixture
from connexion import App
from connexion.decorators.validation import RequestBodyValidator
from connexion.json_schema import Draft4RequestValidator

SPECS = ["swagger.yaml", "openapi.yaml"]

@pytest.mark.parametrize("spec", SPECS)
def test_validator_map(json_validation_spec_dir, spec):
    def validate_type(validator, types, instance, schema):
        types = _utils.ensure_list(types)
        errors = Draft4RequestValidator.VALIDATORS['type'](validator, types, instance, schema)
        for e in errors:
            yield e

        if 'string' in types and 'minLength' not in schema:
            errors = Draft4RequestValidator.VALIDATORS['minLength'](validator, 1, instance, schema)
            for e in errors:
                yield e

    MinLengthRequestValidator = extend(Draft4RequestValidator, {'type': validate_type})

    class MyRequestBodyValidator(RequestBodyValidator):
        def __init__(self, *args, **kwargs):
            super(MyRequestBodyValidator, self).__init__(*args, validator=MinLengthRequestValidator, **kwargs)

    validator_map = {'body': MyRequestBodyValidator}

    app = App(__name__, specification_dir=json_validation_spec_dir)
    app.add_api(spec, validate_responses=True, validator_map=validator_map)
    app_client = app.app.test_client()

    res = app_client.post('/v1.0/minlength', data=json.dumps({'foo': 'bar'}), content_type='application/json') # type: flask.Response
    assert res.status_code == 200

    res = app_client.post('/v1.0/minlength', data=json.dumps({'foo': ''}), content_type='application/json') # type: flask.Response
    assert res.status_code == 400


@pytest.mark.parametrize("spec", SPECS)
def test_readonly(json_validation_spec_dir, spec):
    app = build_app_from_fixture(json_validation_spec_dir, spec, validate_responses=True)
    app_client = app.app.test_client()

    res = app_client.get('/v1.0/user') # type: flask.Response
    assert res.status_code == 200
    assert json.loads(res.data.decode()).get('user_id') == 7

    res = app_client.post('/v1.0/user', data=json.dumps({'name': 'max', 'password': '1234'}), content_type='application/json') # type: flask.Response
    assert res.status_code == 200
    assert json.loads(res.data.decode()).get('user_id') == 8

    res = app_client.post('/v1.0/user', data=json.dumps({'user_id': 9, 'name': 'max'}), content_type='application/json') # type: flask.Response
    assert res.status_code == 400


@pytest.mark.parametrize("spec", SPECS)
def test_writeonly(json_validation_spec_dir, spec):
    app = build_app_from_fixture(json_validation_spec_dir, spec, validate_responses=True)
    app_client = app.app.test_client()

    res = app_client.post('/v1.0/user', data=json.dumps({'name': 'max', 'password': '1234'}), content_type='application/json') # type: flask.Response
    assert res.status_code == 200
    assert 'password' not in json.loads(res.data.decode())

    res = app_client.get('/v1.0/user') # type: flask.Response
    assert res.status_code == 200
    assert 'password' not in json.loads(res.data.decode())

    res = app_client.get('/v1.0/user_with_password') # type: flask.Response
    assert res.status_code == 500
    assert json.loads(res.data.decode())['title'] == 'Response body does not conform to specification'
