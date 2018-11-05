from jsonschema import ValidationError

import pytest
from connexion.decorators.validation import ParameterValidator
from connexion.json_schema import (Draft4RequestValidator,
                                   Draft4ResponseValidator)
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
        Draft4RequestValidator(schema).validate({"foo": None})
    except ValidationError:
        pytest.fail("Shouldn't raise ValidationError")


def test_support_nullable_properties_raises_validation_error():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "x-nullable": False}},
    }

    with pytest.raises(ValidationError):
        Draft4RequestValidator(schema).validate({"foo": None})


def test_support_nullable_properties_not_iterable():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "x-nullable": True}},
    }
    with pytest.raises(ValidationError):
        Draft4RequestValidator(schema).validate(12345)


def test_nullable_enum():
    schema = {
        "enum": ["foo", 7],
        "nullable": True
    }
    try:
        Draft4RequestValidator(schema).validate(None)
    except ValidationError:
        pytest.fail("Shouldn't raise ValidationError")


def test_nullable_enum_error():
    schema = {
        "enum": ["foo", 7]
    }
    with pytest.raises(ValidationError):
        Draft4RequestValidator(schema).validate(None)


def test_writeonly_value():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "writeOnly": True}},
    }
    try:
        Draft4RequestValidator(schema).validate({"foo": "bar"})
    except ValidationError:
        pytest.fail("Shouldn't raise ValidationError")


def test_writeonly_value_error():
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", "writeOnly": True}},
    }
    with pytest.raises(ValidationError):
        Draft4ResponseValidator(schema).validate({"foo": "bar"})


def test_writeonly_required():
    schema = {
        "type": "object",
        "required": ["foo"],
        "properties": {"foo": {"type": "string", "writeOnly": True}},
    }
    try:
        Draft4RequestValidator(schema).validate({"foo": "bar"})
    except ValidationError:
        pytest.fail("Shouldn't raise ValidationError")


def test_writeonly_required_error():
    schema = {
        "type": "object",
        "required": ["foo"],
        "properties": {"foo": {"type": "string", "writeOnly": True}},
    }
    with pytest.raises(ValidationError):
        Draft4RequestValidator(schema).validate({"bar": "baz"})
