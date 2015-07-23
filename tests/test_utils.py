import math

import pytest

import connexion.utils as utils


def test_flaskify_path():
    assert utils.flaskify_path("{test-path}") == "<test_path>"
    assert utils.flaskify_path("api/{test-path}") == "api/<test_path>"
    assert utils.flaskify_path("my-api/{test-path}") == "my-api/<test_path>"
    assert utils.flaskify_path("foo_bar/{a-b}/{c_d}") == "foo_bar/<a_b>/<c_d>"


def test_flaskify_endpoint():
    assert utils.flaskify_endpoint("module.function") == "module_function"
    assert utils.flaskify_endpoint("function") == "function"


def test_get_function_from_name():
    function = utils.get_function_from_name('math.ceil')
    assert function == math.ceil
    assert function(2.7) == 3


def test_parse_datetime():
    utils.parse_datetime('2015-05-05T01:01:01.001+02:00')
    utils.parse_datetime('2015-05-05T01:01:01Z')
    utils.parse_datetime('2015-07-23T18:34:32+02:00')
