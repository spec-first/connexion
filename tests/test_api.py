# coding: utf-8

import pathlib
import tempfile

from yaml import YAMLError

import pytest
from connexion import FlaskApi
from connexion.exceptions import InvalidSpecification, ResolverError
from connexion.spec import canonical_base_path
from mock import MagicMock

TEST_FOLDER = pathlib.Path(__file__).parent


def test_canonical_base_path():
    assert canonical_base_path('') == ''
    assert canonical_base_path('/') == ''
    assert canonical_base_path('/api') == '/api'
    assert canonical_base_path('/api/') == '/api'


def test_api():
    api = FlaskApi(TEST_FOLDER / "fixtures/simple/swagger.yaml", base_path="/api/v1.0")
    assert api.blueprint.name == '/api/v1_0'
    assert api.blueprint.url_prefix == '/api/v1.0'

    api2 = FlaskApi(TEST_FOLDER / "fixtures/simple/swagger.yaml")
    assert api2.blueprint.name == '/v1_0'
    assert api2.blueprint.url_prefix == '/v1.0'

    api3 = FlaskApi(TEST_FOLDER / "fixtures/simple/openapi.yaml", base_path="/api/v1.0")
    assert api3.blueprint.name == '/api/v1_0'
    assert api3.blueprint.url_prefix == '/api/v1.0'

    api4 = FlaskApi(TEST_FOLDER / "fixtures/simple/openapi.yaml")
    assert api4.blueprint.name == '/v1_0'
    assert api4.blueprint.url_prefix == '/v1.0'


def test_api_base_path_slash():
    api = FlaskApi(TEST_FOLDER / "fixtures/simple/basepath-slash.yaml")
    assert api.blueprint.name == ''
    assert api.blueprint.url_prefix == ''


def test_template():
    api1 = FlaskApi(TEST_FOLDER / "fixtures/simple/swagger.yaml",
                    base_path="/api/v1.0", arguments={'title': 'test'})
    assert api1.specification['info']['title'] == 'test'

    api2 = FlaskApi(TEST_FOLDER / "fixtures/simple/swagger.yaml",
                    base_path="/api/v1.0", arguments={'title': 'other test'})
    assert api2.specification['info']['title'] == 'other test'


def test_invalid_operation_does_stop_application_to_setup():
    with pytest.raises(ImportError):
        FlaskApi(TEST_FOLDER / "fixtures/op_error_api/swagger.yaml",
                 base_path="/api/v1.0", arguments={'title': 'OK'})

    with pytest.raises(ValueError):
        FlaskApi(TEST_FOLDER / "fixtures/missing_op_id/swagger.yaml",
                 base_path="/api/v1.0", arguments={'title': 'OK'})

    with pytest.raises(ImportError):
        FlaskApi(TEST_FOLDER / "fixtures/module_not_implemented/swagger.yaml",
                 base_path="/api/v1.0", arguments={'title': 'OK'})

    with pytest.raises(ValueError):
        FlaskApi(TEST_FOLDER / "fixtures/user_module_loading_error/swagger.yaml",
                 base_path="/api/v1.0", arguments={'title': 'OK'})


def test_invalid_operation_does_not_stop_application_in_debug_mode():
    api = FlaskApi(TEST_FOLDER / "fixtures/op_error_api/swagger.yaml",
                   base_path="/api/v1.0", arguments={'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'

    api = FlaskApi(TEST_FOLDER / "fixtures/missing_op_id/swagger.yaml",
                   base_path="/api/v1.0", arguments={'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'

    api = FlaskApi(TEST_FOLDER / "fixtures/module_not_implemented/swagger.yaml",
                   base_path="/api/v1.0", arguments={'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'

    api = FlaskApi(TEST_FOLDER / "fixtures/user_module_loading_error/swagger.yaml",
                   base_path="/api/v1.0", arguments={'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'


def test_other_errors_stop_application_to_setup():
    # Errors should still result exceptions!
    with pytest.raises(InvalidSpecification):
        FlaskApi(TEST_FOLDER / "fixtures/bad_specs/swagger.yaml",
                 base_path="/api/v1.0", arguments={'title': 'OK'})


def test_invalid_schema_file_structure():
    with pytest.raises(InvalidSpecification):
        FlaskApi(TEST_FOLDER / "fixtures/invalid_schema/swagger.yaml",
                 base_path="/api/v1.0", arguments={'title': 'OK'}, debug=True)


def test_invalid_encoding():
    with tempfile.NamedTemporaryFile(mode='wb') as f:
        f.write(u"swagger: '2.0'\ninfo:\n  title: Foo 整\n  version: v1\npaths: {}".encode('gbk'))
        f.flush()
        FlaskApi(pathlib.Path(f.name), base_path="/api/v1.0")


def test_use_of_safe_load_for_yaml_swagger_specs():
    with pytest.raises(YAMLError):
        with tempfile.NamedTemporaryFile() as f:
            f.write('!!python/object:object {}\n'.encode())
            f.flush()
            try:
                FlaskApi(pathlib.Path(f.name), base_path="/api/v1.0")
            except InvalidSpecification:
                pytest.fail("Could load invalid YAML file, use yaml.safe_load!")


def test_validation_error_on_completely_invalid_swagger_spec():
    with pytest.raises(InvalidSpecification):
        with tempfile.NamedTemporaryFile() as f:
            f.write('[1]\n'.encode())
            f.flush()
            FlaskApi(pathlib.Path(f.name), base_path="/api/v1.0")


@pytest.fixture
def mock_api_logger(monkeypatch):
    mocked_logger = MagicMock(name='mocked_logger')
    monkeypatch.setattr('connexion.apis.abstract.logger', mocked_logger)
    return mocked_logger
