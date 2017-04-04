import math

import connexion.apps
from connexion import utils
import pytest

from mock import MagicMock


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
