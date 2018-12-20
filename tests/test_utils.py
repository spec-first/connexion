import math

import six

import connexion.apps
import pytest
from conftest import ENCODING_STRINGS
from connexion import utils
from mock import MagicMock


def test_get_function_from_name():
    function = utils.get_function_from_name('math.ceil')
    assert function == math.ceil
    assert function(2.7) == 3


def test_get_function_from_name_no_module():
    with pytest.raises(ValueError):
        utils.get_function_from_name('math')


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
    function = utils.get_function_from_name('connexion.FlaskApp.common_error_handler')
    assert function == connexion.FlaskApp.common_error_handler


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


@pytest.mark.parametrize("data", ENCODING_STRINGS)
def test_decode(data):
    assert isinstance(utils.decode(data), six.text_type)


@pytest.mark.parametrize("data", ENCODING_STRINGS)
def test_encode(data):
    assert isinstance(utils.encode(data), six.binary_type)


@pytest.mark.parametrize("obj,length,expected", [
    [(1,), 3, (1, None, None)],
    [(1, 2), 2, (1, 2)]
])
def test_normalize_tuple(obj, length, expected):
    assert utils.normalize_tuple(obj, length) == expected


@pytest.mark.parametrize("obj,length", [
    ["1", 1],
    [(1, 2), 1]
])
@pytest.mark.xfail(raises=ValueError)
def test_normalize_tuple_wrong_data(obj, length):
    utils.normalize_tuple(obj, length)


@pytest.mark.parametrize("obj,expected", [
    ("test", True),
    (b"test", True),
    ({}, False),
    (None, False),
    ([], False),
    (1, False)
])
def test_is_string(obj, expected):
    assert utils.is_string(obj) is expected
