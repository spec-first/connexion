# coding: utf-8

import pathlib
import tempfile
from mock import patch

import pytest
from connexion.api import Api
from swagger_spec_validator.common import SwaggerValidationError

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


def test_invalid_operation_does_not_stop_application_in_debug_mode():
    api = Api(TEST_FOLDER / "fakeapi/op_error_api.yaml", "/api/v1.0",
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
