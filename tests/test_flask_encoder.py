import datetime
import json
import math
from decimal import Decimal

import pytest
from connexion.frameworks.flask import FlaskJSONProvider

from conftest import build_app_from_fixture

SPECS = ["swagger.yaml", "openapi.yaml"]


def test_json_encoder(simple_app):
    flask_app = simple_app.app

    s = FlaskJSONProvider(flask_app).dumps({1: 2})
    assert '{"1": 2}' == s

    s = FlaskJSONProvider(flask_app).dumps(datetime.date.today())
    assert len(s) == 12

    s = FlaskJSONProvider(flask_app).dumps(datetime.datetime.utcnow())
    assert s.endswith('Z"')

    s = FlaskJSONProvider(flask_app).dumps(Decimal(1.01))
    assert s == "1.01"

    s = FlaskJSONProvider(flask_app).dumps(math.expm1(1e-10))
    assert s == "1.00000000005e-10"


def test_json_encoder_datetime_with_timezone(simple_app):
    class DummyTimezone(datetime.tzinfo):
        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def dst(self, dt):
            return datetime.timedelta(0)

    flask_app = simple_app.app
    s = FlaskJSONProvider(flask_app).dumps(datetime.datetime.now(DummyTimezone()))
    assert s.endswith('+00:00"')


@pytest.mark.parametrize("spec", SPECS)
def test_readonly(json_datetime_dir, spec):
    app = build_app_from_fixture(json_datetime_dir, spec, validate_responses=True)
    app_client = app.test_client()

    res = app_client.get("/v1.0/" + spec.replace("yaml", "json"))
    assert res.status_code == 200, f"Error is {res.data}"
    spec_data = json.loads(res.data.decode())

    if spec == "openapi.yaml":
        response_path = "responses.200.content.application/json.schema"
    else:
        response_path = "responses.200.schema"

    def get_value(data, path):
        for part in path.split("."):
            data = data.get(part)
            assert data, f"No data in part '{part}' of '{path}'"
        return data

    example = get_value(spec_data, f"paths./datetime.get.{response_path}.example.value")
    assert example in [
        "2000-01-23T04:56:07.000008+00:00",  # PyYAML 5.3+
        "2000-01-23T04:56:07.000008Z",
    ]
    example = get_value(spec_data, f"paths./date.get.{response_path}.example.value")
    assert example == "2000-01-23"
    example = get_value(spec_data, f"paths./uuid.get.{response_path}.example.value")
    assert example == "a7b8869c-5f24-4ce0-a5d1-3e44c3663aa9"

    res = app_client.get("/v1.0/datetime")
    assert res.status_code == 200, f"Error is {res.data}"
    data = json.loads(res.data.decode())
    assert data == {"value": "2000-01-02T03:04:05.000006Z"}

    res = app_client.get("/v1.0/date")
    assert res.status_code == 200, f"Error is {res.data}"
    data = json.loads(res.data.decode())
    assert data == {"value": "2000-01-02"}

    res = app_client.get("/v1.0/uuid")
    assert res.status_code == 200, f"Error is {res.data}"
    data = json.loads(res.data.decode())
    assert data == {"value": "e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51"}
