import datetime
import json
import math
from decimal import Decimal

from connexion.frameworks.flask import FlaskJSONProvider

from conftest import build_app_from_fixture


def test_json_encoder():
    json_encoder = json.JSONEncoder
    json_encoder.default = FlaskJSONProvider.default

    s = json.dumps({1: 2}, cls=json_encoder)
    assert '{"1": 2}' == s

    s = json.dumps(datetime.date.today(), cls=json_encoder)
    assert len(s) == 12

    s = json.dumps(datetime.datetime.utcnow(), cls=json_encoder)
    assert s.endswith('Z"')

    s = json.dumps(Decimal(1.01), cls=json_encoder)
    assert s == "1.01"

    s = json.dumps(math.expm1(1e-10), cls=json_encoder)
    assert s == "1.00000000005e-10"


def test_json_encoder_datetime_with_timezone():
    json_encoder = json.JSONEncoder
    json_encoder.default = FlaskJSONProvider.default

    class DummyTimezone(datetime.tzinfo):
        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def dst(self, dt):
            return datetime.timedelta(0)

    s = json.dumps(datetime.datetime.now(DummyTimezone()), cls=json_encoder)
    assert s.endswith('+00:00"')


def test_readonly(json_datetime_dir, spec, app_class):
    app = build_app_from_fixture(
        json_datetime_dir, app_class=app_class, spec_file=spec, validate_responses=True
    )
    app_client = app.test_client()

    res = app_client.get("/v1.0/" + spec.replace("yaml", "json"))
    assert res.status_code == 200, f"Error is {res.text}"
    spec_data = res.json()

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
    assert res.status_code == 200, f"Error is {res.text}"
    data = res.json()
    assert data == {"value": "2000-01-02T03:04:05.000006Z"}

    res = app_client.get("/v1.0/date")
    assert res.status_code == 200, f"Error is {res.text}"
    data = res.json()
    assert data == {"value": "2000-01-02"}

    res = app_client.get("/v1.0/uuid")
    assert res.status_code == 200, f"Error is {res.text}"
    data = res.json()
    assert data == {"value": "e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51"}
