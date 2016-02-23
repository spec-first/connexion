import pathlib

import pytest
from connexion.api import Api

TEST_FOLDER = pathlib.Path(__file__).parent


def test_api():
    api = Api(TEST_FOLDER / "fakeapi/api.yaml", "/api/v1.0", {})
    assert api.blueprint.name == '/api/v1_0'
    assert api.blueprint.url_prefix == '/api/v1.0'
    # TODO test base_url in spec

    api2 = Api(TEST_FOLDER / "fakeapi/api.yaml")
    assert api2.blueprint.name == '/v1_0'
    assert api2.blueprint.url_prefix == '/v1.0'


def test_template():
    api1 = Api(TEST_FOLDER / "fakeapi/api.yaml", "/api/v1.0", {'title': 'test'})
    assert api1.specification['info']['title'] == 'test'

    api2 = Api(TEST_FOLDER / "fakeapi/api.yaml", "/api/v1.0", {'title': 'other test'})
    assert api2.specification['info']['title'] == 'other test'


def test_invalid_operation_does_stop_application_to_setup():
    with pytest.raises(AttributeError):
        Api(TEST_FOLDER / "fakeapi/op_error_api.yaml", "/api/v1.0", {})
