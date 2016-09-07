import math

import connexion.app
import connexion.utils as utils

import pytest
from mock import MagicMock


def test_flaskify_path():
    assert utils.flaskify_path("{test-path}") == "<test_path>"
    assert utils.flaskify_path("api/{test-path}") == "api/<test_path>"
    assert utils.flaskify_path("my-api/{test-path}") == "my-api/<test_path>"
    assert utils.flaskify_path("foo_bar/{a-b}/{c_d}") == "foo_bar/<a_b>/<c_d>"
    assert utils.flaskify_path("foo/{a}/{b}", {'a': 'integer'}) == "foo/<int:a>/<b>"
    assert utils.flaskify_path("foo/{a}/{b}", {'a': 'number'}) == "foo/<float:a>/<b>"


def test_flaskify_endpoint():
    assert utils.flaskify_endpoint("module.function") == "module_function"
    assert utils.flaskify_endpoint("function") == "function"

    name = 'module.function'
    randlen = 6
    res = utils.flaskify_endpoint(name, randlen)
    assert res.startswith('module_function')
    assert len(res) == len(name) + 1 + randlen


def test_get_function_from_name():
    function = utils.get_function_from_name('math.ceil')
    assert function == math.ceil
    assert function(2.7) == 3


def test_get_function_from_name_attr_error(monkeypatch):
    """
    Test attribute error without import error on get_function_from_name.
    Attribute errors due to import errors are tested on
    test_api.test_invalid_operation_does_stop_application_to_setup
    """
    deep_attr_mock = MagicMock()
    deep_attr_mock.side_effect = AttributeError
    monkeypatch.setattr("connexion.utils.deep_getattr", deep_attr_mock)
    with pytest.raises(AttributeError):
        utils.get_function_from_name('math.ceil')


def test_get_function_from_name_for_class_method():
    function = utils.get_function_from_name('connexion.app.App.common_error_handler')
    assert function == connexion.app.App.common_error_handler


def test_boolean():
    assert utils.boolean('true')
    assert utils.boolean('True')
    assert utils.boolean('TRUE')
    assert utils.boolean(True)
    assert not utils.boolean('false')
    assert not utils.boolean('False')
    assert not utils.boolean('FALSE')
    assert not utils.boolean(False)

    with pytest.raises(ValueError):
        utils.boolean('foo')

    with pytest.raises(ValueError):
        utils.boolean(None)
