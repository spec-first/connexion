# coding: utf-8

import pathlib
import tempfile

from connexion.api import Api
from connexion.exceptions import ResolverError
from connexion.exceptions import InvalidSpecification
from swagger_spec_validator.common import SwaggerValidationError
from yaml import YAMLError

import pytest

TEST_FOLDER = pathlib.Path(__file__).parent


def test_api():
    api = Api(TEST_FOLDER / "fixtures/simple/swagger.yaml", "/api/v1.0", {})
    assert api.blueprint.name == '/api/v1_0'
    assert api.blueprint.url_prefix == '/api/v1.0'
    # TODO test base_url in spec

    api2 = Api(TEST_FOLDER / "fixtures/simple/swagger.yaml")
    assert api2.blueprint.name == '/v1_0'
    assert api2.blueprint.url_prefix == '/v1.0'


def test_template():
    api1 = Api(TEST_FOLDER / "fixtures/simple/swagger.yaml", "/api/v1.0", {'title': 'test'})
    assert api1.specification['info']['title'] == 'test'

    api2 = Api(TEST_FOLDER / "fixtures/simple/swagger.yaml", "/api/v1.0", {'title': 'other test'})
    assert api2.specification['info']['title'] == 'other test'


def test_invalid_operation_does_stop_application_to_setup():
    with pytest.raises(ImportError):
        Api(TEST_FOLDER / "fakeapi/op_error_api.yaml", "/api/v1.0",
            {'title': 'OK'})
    with pytest.raises(ResolverError):
        Api(TEST_FOLDER / "fakeapi/missing_op_id.yaml", "/api/v1.0",
            {'title': 'OK'})


def test_invalid_operation_does_not_stop_application_in_debug_mode():
    api = Api(TEST_FOLDER / "fakeapi/op_error_api.yaml", "/api/v1.0",
              {'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'

    api = Api(TEST_FOLDER / "fakeapi/missing_op_id.yaml", "/api/v1.0",
              {'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'


def test_other_errors_stop_application_to_setup():
    # The previous tests were just about operationId not being resolvable.
    # Other errors should still result exceptions!
    #with pytest.raises(ResolverError):
    with pytest.raises(InvalidSpecification):
        Api(TEST_FOLDER / "fakeapi/bad_specs.yaml", "/api/v1.0",
            {'title': 'OK'})

    # Debug mode should ignore the error
    api = Api(TEST_FOLDER / "fakeapi/bad_specs.yaml", "/api/v1.0",
        {'title': 'OK'}, debug=True)
    assert api.specification['info']['title'] == 'OK'


def test_invalid_schema_file_structure():
    with pytest.raises(SwaggerValidationError):
        Api(TEST_FOLDER / "fixtures/invalid_schema/swagger.yaml", "/api/v1.0",
            {'title': 'OK'}, debug=True)


def test_invalid_encoding():
    with tempfile.NamedTemporaryFile(mode='wb') as f:
        f.write(u"swagger: '2.0'\ninfo:\n  title: Foo 整\n  version: v1\npaths: {}".encode('gbk'))
        f.flush()
        Api(pathlib.Path(f.name), "/api/v1.0")


def test_use_of_safe_load_for_yaml_swagger_specs():
    with pytest.raises(YAMLError):
        with tempfile.NamedTemporaryFile() as f:
            f.write('!!python/object:object {}\n'.encode())
            f.flush()
            try:
                Api(pathlib.Path(f.name), "/api/v1.0")
            except SwaggerValidationError:
                pytest.fail("Could load invalid YAML file, use yaml.safe_load!")


def test_validation_error_on_completely_invalid_swagger_spec():
    with pytest.raises(SwaggerValidationError):
        with tempfile.NamedTemporaryFile() as f:
            f.write('[1]\n'.encode())
            f.flush()
            Api(pathlib.Path(f.name), "/api/v1.0")
