import json
import pathlib

import pytest
from connexion import App
from connexion.json_schema import Draft4RequestValidator
from connexion.spec import Specification
from connexion.validators import JSONRequestBodyValidator
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
        def __init__(self, *args, **kwargs):
            super().__init__(*args, validator=MinLengthRequestValidator, **kwargs)

    validator_map = {"body": {"application/json": MyJSONBodyValidator}}

    app = App(__name__, specification_dir=json_validation_spec_dir)
    app.add_api(spec, validate_responses=True, validator_map=validator_map)
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/minlength",
        data=json.dumps({"foo": "bar"}),
        content_type="application/json",
    )
    assert res.status_code == 200

    res = app_client.post(
        "/v1.0/minlength", data=json.dumps({"foo": ""}), content_type="application/json"
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

    headers = {"content-type": "application/json"}

    res = app_client.get("/v1.0/user")
    assert res.status_code == 200
    assert json.loads(res.text).get("user_id") == 7

    res = app_client.post(
        "/v1.0/user",
        data=json.dumps({"name": "max", "password": "1234"}),
        headers=headers,
    )
    assert res.status_code == 200
    assert json.loads(res.text).get("user_id") == 8

    res = app_client.post(
        "/v1.0/user",
        data=json.dumps({"user_id": 9, "name": "max"}),
        headers=headers,
    )
    assert res.status_code == 400


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
        data=json.dumps({"name": "max", "password": "1234"}),
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 200
    assert "password" not in json.loads(res.text)

    res = app_client.get("/v1.0/user")
    assert res.status_code == 200
    assert "password" not in json.loads(res.text)

    res = app_client.get("/v1.0/user_with_password")
    assert res.status_code == 500
    assert (
        json.loads(res.text)["title"]
        == "Response body does not conform to specification"
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
        data={"x": json.dumps({"name": "joe", "age": 20})},
        headers={"content-type": "multipart/form-data"},
    )
    assert res.status_code == 200
    assert json.loads(res.text)["name"] == "joe-reply"
    assert json.loads(res.text)["age"] == 30
