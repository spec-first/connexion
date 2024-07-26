import json
import pathlib

import pytest
from connexion import App
from connexion.json_schema import Draft4RequestValidator
from connexion.spec import Specification
from connexion.validators import (
    DefaultsJSONRequestBodyValidator,
    JSONRequestBodyValidator,
)
from jsonschema.validators import _utils, extend

from conftest import build_app_from_fixture


def test_validator_map(json_validation_spec_dir, spec):
    def validate_type(validator, types, instance, schema):
        types = _utils.ensure_list(types)
        errors = Draft4RequestValidator.VALIDATORS["type"](
            validator, types, instance, schema
        )
        yield from errors

        if "string" in types and "minLength" not in schema:
            errors = Draft4RequestValidator.VALIDATORS["minLength"](
                validator, 1, instance, schema
            )
            yield from errors

    MinLengthRequestValidator = extend(Draft4RequestValidator, {"type": validate_type})

    class MyJSONBodyValidator(JSONRequestBodyValidator):
        @property
        def _validator(self):
            return MinLengthRequestValidator(self._schema)

    validator_map = {"body": {"application/json": MyJSONBodyValidator}}

    app = App(__name__, specification_dir=json_validation_spec_dir)
    app.add_api(spec, validate_responses=True, validator_map=validator_map)
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/minlength",
        json={"foo": "bar"},
    )
    assert res.status_code == 200

    res = app_client.post(
        "/v1.0/minlength",
        json={"foo": ""},
    )
    assert res.status_code == 400


def test_readonly(json_validation_spec_dir, spec, app_class):
    app = build_app_from_fixture(
        json_validation_spec_dir,
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
    )
    app_client = app.test_client()

    res = app_client.get("/v1.0/user")
    assert res.status_code == 200
    assert res.json().get("user_id") == 7

    res = app_client.post(
        "/v1.0/user",
        json={"name": "max", "password": "1234"},
    )
    assert res.status_code == 200
    assert res.json().get("user_id") == 8

    res = app_client.post(
        "/v1.0/user",
        json={"user_id": 9, "name": "max"},
    )
    assert res.status_code == 200


def test_writeonly(json_validation_spec_dir, spec, app_class):
    app = build_app_from_fixture(
        json_validation_spec_dir,
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
    )
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/user",
        json={"name": "max", "password": "1234"},
    )
    assert res.status_code == 200
    assert "password" not in res.json()

    res = app_client.get("/v1.0/user")
    assert res.status_code == 200
    assert "password" not in res.json()

    res = app_client.get("/v1.0/user_with_password")
    assert res.status_code == 500
    assert res.json()["detail"].startswith(
        "Response body does not conform to specification"
    )


def test_nullable_default(json_validation_spec_dir, spec):
    spec_path = pathlib.Path(json_validation_spec_dir) / spec
    Specification.load(spec_path)


@pytest.mark.parametrize("spec", ["openapi.yaml"])
def test_multipart_form_json(json_validation_spec_dir, spec, app_class):
    app = build_app_from_fixture(
        json_validation_spec_dir,
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
    )
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/multipart_form_json",
        files={"file": b""},  # Force multipart/form-data content-type
        data={"x": json.dumps({"name": "joe", "age": 20})},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "joe-reply"
    assert res.json()["age"] == 30


@pytest.mark.parametrize("spec", ["openapi.yaml"])
def test_multipart_form_json_array(json_validation_spec_dir, spec, app_class):
    app = build_app_from_fixture(
        json_validation_spec_dir,
        app_class=app_class,
        spec_file=spec,
        validate_responses=True,
    )
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/multipart_form_json_array",
        files={"file": b""},  # Force multipart/form-data content-type
        data={
            "x": json.dumps([{"name": "joe", "age": 20}, {"name": "alena", "age": 28}])
        },
    )
    assert res.status_code == 200
    assert res.json()[0]["name"] == "joe-reply"
    assert res.json()[0]["age"] == 30
    assert res.json()[1]["name"] == "alena-reply"
    assert res.json()[1]["age"] == 38


def test_defaults_body(json_validation_spec_dir, spec):
    """ensure that defaults applied that modify the body"""

    class MyDefaultsJSONBodyValidator(DefaultsJSONRequestBodyValidator):
        pass

    validator_map = {"body": {"application/json": MyDefaultsJSONBodyValidator}}

    app = App(__name__, specification_dir=json_validation_spec_dir)
    app.add_api(spec, validate_responses=True, validator_map=validator_map)
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/user",
        json={"name": "foo"},
    )
    assert res.status_code == 200
    assert res.json().get("human")
