import datetime
import json
import math
from decimal import Decimal

import pytest
from connexion.apps.flask_app import FlaskJSONEncoder

from conftest import build_app_from_fixture

SPECS = ["swagger.yaml", "openapi.yaml"]


def test_json_encoder():
    s = json.dumps({1: 2}, cls=FlaskJSONEncoder)
    assert '{"1": 2}' == s

    s = json.dumps(datetime.date.today(), cls=FlaskJSONEncoder)
    assert len(s) == 12

    s = json.dumps(datetime.datetime.utcnow(), cls=FlaskJSONEncoder)
    assert s.endswith('Z"')

    s = json.dumps(Decimal(1.01), cls=FlaskJSONEncoder)
    assert s == '1.01'

    s = json.dumps(math.expm1(1e-10), cls=FlaskJSONEncoder)
    assert s == '1.00000000005e-10'


def test_json_encoder_datetime_with_timezone():

    class DummyTimezone(datetime.tzinfo):

        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def dst(self, dt):
            return datetime.timedelta(0)

    s = json.dumps(datetime.datetime.now(DummyTimezone()), cls=FlaskJSONEncoder)
    assert s.endswith('+00:00"')


@pytest.mark.parametrize("spec", SPECS)
def test_readonly(json_datetime_dir, spec):
    app = build_app_from_fixture(json_datetime_dir, spec, validate_responses=True)
    app_client = app.app.test_client()

    res = app_client.get('/v1.0/' + spec.replace('yaml', 'json'))
    assert res.status_code == 200, "Error is {}".format(res.data)
    spec_data = json.loads(res.data.decode())

    if spec == 'openapi.yaml':
        response_path = 'responses.200.content.application/json.schema'
    else:
        response_path = 'responses.200.schema'

    def get_value(data, path):
        for part in path.split('.'):
            data = data.get(part)
            assert data, "No data in part '{}' of '{}'".format(part, path)
        return data

    example = get_value(spec_data, 'paths./datetime.get.{}.example.value'.format(response_path))
    assert example in [
        '2000-01-23T04:56:07.000008+00:00',  # PyYAML 5.3+
        '2000-01-23T04:56:07.000008Z'
    ]
    example = get_value(spec_data, 'paths./date.get.{}.example.value'.format(response_path))
    assert example == '2000-01-23'
    example = get_value(spec_data, 'paths./uuid.get.{}.example.value'.format(response_path))
    assert example == 'a7b8869c-5f24-4ce0-a5d1-3e44c3663aa9'

    res = app_client.get('/v1.0/datetime')
    assert res.status_code == 200, "Error is {}".format(res.data)
    data = json.loads(res.data.decode())
    assert data == {'value': '2000-01-02T03:04:05.000006Z'}

    res = app_client.get('/v1.0/date')
    assert res.status_code == 200, "Error is {}".format(res.data)
    data = json.loads(res.data.decode())
    assert data == {'value': '2000-01-02'}

    res = app_client.get('/v1.0/uuid')
    assert res.status_code == 200, "Error is {}".format(res.data)
    data = json.loads(res.data.decode())
    assert data == {'value': 'e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51'}
