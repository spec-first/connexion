from jsonschema import ValidationError

import pytest
from connexion.decorators.validation import (Draft4ValidatorSupportNullable,
                                             ParameterValidator)
from mock import MagicMock


def test_get_valid_parameter():
    result = ParameterValidator.validate_parameter('formdata', 20, {'type': 'number', 'name': 'foobar'})
    assert result is None


def test_get_valid_parameter_with_required_attr():
    param = {'type': 'number', 'required': True, 'name': 'foobar'}
    result = ParameterValidator.validate_parameter('formdata', 20, param)
    assert result is None


def test_get_missing_required_parameter():
    param = {'type': 'number', 'required': True, 'name': 'foo'}
    result = ParameterValidator.validate_parameter('formdata', None, param)
    assert result == "Missing formdata parameter 'foo'"


def test_get_nullable_parameter():
    param = {'type': 'number', 'required': True, 'name': 'foo', 'x-nullable': True}
    result = ParameterValidator.validate_parameter('formdata', 'None', param)
    assert result is None


def test_invalid_type(monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr('connexion.decorators.validation.logger', logger)
    result = ParameterValidator.validate_parameter('formdata', 20, {'type': 'string', 'name': 'foo'})
    expected_result = """20 is not of type 'string'

Failed validating 'type' in schema:
    {'name': 'foo', 'type': 'string'}

On instance:
    20"""
    assert result == expected_result
    logger.info.assert_called_once()


def test_invalid_type_value_error(monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr('connexion.decorators.validation.logger', logger)
    value = {'test': 1, 'second': 2}
    result = ParameterValidator.validate_parameter('formdata', value, {'type': 'boolean', 'name': 'foo'})
    assert result == "Wrong type, expected 'boolean' for formdata parameter 'foo'"

def test_support_nullable_properties():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "x-nullable": True}},
    }
    try:
        Draft4ValidatorSupportNullable(schema).validate({"foo": None})
    except ValidationError:
        pytest.fail("Shouldn't raise ValidationError")


def test_support_nullable_properties_raises_validation_error():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "x-nullable": False}},
    }

    with pytest.raises(ValidationError):
        Draft4ValidatorSupportNullable(schema).validate({"foo": None})


def test_support_nullable_properties_not_iterable():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "x-nullable": True}},
    }
    with pytest.raises(ValidationError):
        Draft4ValidatorSupportNullable(schema).validate(12345)
