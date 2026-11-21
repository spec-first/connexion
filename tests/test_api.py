import os
import pathlib
import tempfile
from unittest.mock import MagicMock

import pytest
from connexion import FlaskApi
from connexion.exceptions import InvalidSpecification, ResolverError
from connexion.jsonifier import Jsonifier
from connexion.spec import Specification, canonical_base_path
from yaml import YAMLError

TEST_FOLDER = pathlib.Path(__file__).parent


def test_canonical_base_path():
    assert canonical_base_path("") == ""
    assert canonical_base_path("/") == ""
    assert canonical_base_path("/api") == "/api"
    assert canonical_base_path("/api/") == "/api"


def _swagger2_spec(base_path=None):
    spec = {
        "swagger": "2.0",
        "info": {"title": "t", "version": "1.0"},
        "paths": {},
    }
    if base_path is not None:
        spec["basePath"] = base_path
    return spec


def test_swagger2_empty_base_path_is_omitted():
    # A spec without basePath must not gain an empty, schema-invalid
    # basePath when served without a proxy prefix.
    spec = Specification.from_dict(_swagger2_spec())
    served = spec.with_base_path("").spec
    assert "basePath" not in served
    assert spec.with_base_path("").base_path == ""


def test_swagger2_slash_base_path_is_omitted():
    # basePath "/" canonicalizes to "" and is equivalent to no base
    # path, so it must not be served as an empty string either.
    spec = Specification.from_dict(_swagger2_spec("/"))
    served = spec.with_base_path("").spec
    assert "basePath" not in served


def test_swagger2_nonempty_base_path_is_kept():
    spec = Specification.from_dict(_swagger2_spec("/v1"))
    served = spec.with_base_path("/behind/proxy").spec
    assert served["basePath"] == "/behind/proxy"


def test_api():
    api = FlaskApi(
        Specification.load(TEST_FOLDER / "fixtures/simple/swagger.yaml"),
        base_path="/api/v1.0",
    )
    assert api.blueprint.name == "/api/v1_0"
    assert api.blueprint.url_prefix == "/api/v1.0"

    api2 = FlaskApi(Specification.load(TEST_FOLDER / "fixtures/simple/swagger.yaml"))
    assert api2.blueprint.name == "/v1_0"
    assert api2.blueprint.url_prefix == "/v1.0"

    api3 = FlaskApi(
        Specification.load(TEST_FOLDER / "fixtures/simple/openapi.yaml"),
        base_path="/api/v1.0",
    )
    assert api3.blueprint.name == "/api/v1_0"
    assert api3.blueprint.url_prefix == "/api/v1.0"

    api4 = FlaskApi(Specification.load(TEST_FOLDER / "fixtures/simple/openapi.yaml"))
    assert api4.blueprint.name == "/v1_0"
    assert api4.blueprint.url_prefix == "/v1.0"


def test_api_base_path_slash():
    api = FlaskApi(
        Specification.load(TEST_FOLDER / "fixtures/simple/basepath-slash.yaml")
    )
    assert api.blueprint.name == "/"
    assert api.blueprint.url_prefix == ""


def test_remote_api():
    api = FlaskApi(
        Specification.load(
            "https://raw.githubusercontent.com/spec-first/connexion/165a915/tests/fixtures/simple/swagger.yaml"
        ),
        base_path="/api/v1.0",
    )
    assert api.blueprint.name == "/api/v1_0"
    assert api.blueprint.url_prefix == "/api/v1.0"

    api2 = FlaskApi(
        Specification.load(
            "https://raw.githubusercontent.com/spec-first/connexion/165a915/tests/fixtures/simple/swagger.yaml"
        )
    )
    assert api2.blueprint.name == "/v1_0"
    assert api2.blueprint.url_prefix == "/v1.0"

    api3 = FlaskApi(
        Specification.load(
            "https://raw.githubusercontent.com/spec-first/connexion/165a915/tests/fixtures/simple/openapi.yaml"
        ),
        base_path="/api/v1.0",
    )
    assert api3.blueprint.name == "/api/v1_0"
    assert api3.blueprint.url_prefix == "/api/v1.0"

    api4 = FlaskApi(
        Specification.load(
            "https://raw.githubusercontent.com/spec-first/connexion/165a915/tests/fixtures/simple/openapi.yaml"
        )
    )
    assert api4.blueprint.name == "/v1_0"
    assert api4.blueprint.url_prefix == "/v1.0"


def test_template():
    api1 = FlaskApi(
        Specification.load(
            TEST_FOLDER / "fixtures/simple/swagger.yaml", arguments={"title": "test"}
        ),
        base_path="/api/v1.0",
    )
    assert api1.specification["info"]["title"] == "test"

    api2 = FlaskApi(
        Specification.load(
            TEST_FOLDER / "fixtures/simple/swagger.yaml",
            arguments={"title": "other test"},
        ),
        base_path="/api/v1.0",
    )
    assert api2.specification["info"]["title"] == "other test"


def test_invalid_operation_does_stop_application_to_setup():
    with pytest.raises(ResolverError):
        FlaskApi(
            Specification.load(
                TEST_FOLDER / "fixtures/op_error_api/swagger.yaml",
                arguments={"title": "OK"},
            ),
            base_path="/api/v1.0",
        )

    with pytest.raises(ResolverError):
        FlaskApi(
            Specification.load(
                TEST_FOLDER / "fixtures/missing_op_id/swagger.yaml",
                arguments={"title": "OK"},
            ),
            base_path="/api/v1.0",
        )

    with pytest.raises(ResolverError):
        FlaskApi(
            Specification.load(
                TEST_FOLDER / "fixtures/module_not_implemented/swagger.yaml",
                arguments={"title": "OK"},
            ),
            base_path="/api/v1.0",
        )

    with pytest.raises(ResolverError):
        FlaskApi(
            Specification.load(
                TEST_FOLDER / "fixtures/user_module_loading_error/swagger.yaml",
                arguments={"title": "OK"},
            ),
            base_path="/api/v1.0",
        )


def test_other_errors_stop_application_to_setup():
    # Errors should still result exceptions!
    with pytest.raises(InvalidSpecification):
        FlaskApi(
            Specification.load(
                TEST_FOLDER / "fixtures/bad_specs/swagger.yaml",
                arguments={"title": "OK"},
            ),
            base_path="/api/v1.0",
        )


def test_invalid_schema_file_structure():
    with pytest.raises(InvalidSpecification):
        FlaskApi(
            Specification.load(
                TEST_FOLDER / "fixtures/invalid_schema/swagger.yaml",
                arguments={"title": "OK"},
            ),
            base_path="/api/v1.0",
        )


def test_invalid_encoding():
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(
            "swagger: '2.0'\ninfo:\n  title: Foo 整\n  version: v1\npaths: {}".encode(
                "gbk"
            )
        )
    FlaskApi(Specification.load(pathlib.Path(f.name)), base_path="/api/v1.0")
    os.unlink(f.name)


def test_use_of_safe_load_for_yaml_swagger_specs():
    with pytest.raises(YAMLError):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"!!python/object:object {}\n")
        try:
            FlaskApi(Specification.load(pathlib.Path(f.name)), base_path="/api/v1.0")
            os.unlink(f.name)
        except InvalidSpecification:
            pytest.fail("Could load invalid YAML file, use yaml.safe_load!")


def test_validation_error_on_completely_invalid_swagger_spec():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"[1]\n")
    with pytest.raises(InvalidSpecification):
        FlaskApi(Specification.load(pathlib.Path(f.name)), base_path="/api/v1.0")
    os.unlink(f.name)


def test_relative_refs(relative_refs, spec):
    jsonifier = Jsonifier()

    spec_path = relative_refs / spec
    specification = Specification.load(spec_path)

    assert "$ref" in jsonifier.dumps(specification.raw)
    assert "$ref" not in jsonifier.dumps(specification.spec)

    cloned_specification = specification.clone()

    assert "$ref" in jsonifier.dumps(cloned_specification.raw)
    assert "$ref" not in jsonifier.dumps(cloned_specification.spec)


@pytest.fixture
def mock_api_logger(monkeypatch):
    mocked_logger = MagicMock(name="mocked_logger")
    monkeypatch.setattr("connexion.apis.abstract.logger", mocked_logger)
    return mocked_logger
