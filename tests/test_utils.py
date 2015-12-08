import math

import pytest

import connexion.app
import connexion.utils as utils


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


def test_get_function_from_name():
    function = utils.get_function_from_name('math.ceil')
    assert function == math.ceil
    assert function(2.7) == 3


def test_get_function_from_name_for_class_method():
    function = utils.get_function_from_name('connexion.app.App.common_error_handler')
    assert function == connexion.app.App.common_error_handler


def test_validate_date():
    assert not utils.validate_date('foo')
    assert utils.validate_date('2015-07-31')
    assert not utils.validate_date('2015-07-31T19:51:00Z')
    assert utils.validate_date('9999-12-31')


def test_boolean():
    assert utils.boolean('true')
    assert not utils.boolean('false')
