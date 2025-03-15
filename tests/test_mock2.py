from datetime import datetime
from re import fullmatch

from connexion.utils import build_example_from_schema


def test_build_example_from_schema_string():
    schema = {
        "type": "string",
    }
    example = build_example_from_schema(schema)
    assert isinstance(example, str)


def test_build_example_from_schema_integer():
    schema = {
        "type": "integer",
    }
    example = build_example_from_schema(schema)
    assert isinstance(example, int)


def test_build_example_from_schema_number():
    schema = {
        "type": "number",
    }
    example = build_example_from_schema(schema)
    assert isinstance(example, float)


def test_build_example_from_schema_boolean():
    schema = {
        "type": "boolean",
    }
    example = build_example_from_schema(schema)
    assert isinstance(example, bool)


def test_build_example_from_schema_integer_minimum():
    schema = {
        "type": "integer",
        "minimum": 4,
    }
    example = build_example_from_schema(schema)
    assert example >= schema["minimum"] and isinstance(example, int)


def test_build_example_from_schema_integer_maximum():
    schema = {
        "type": "integer",
        "maximum": 17,
    }
    example = build_example_from_schema(schema)
    assert example <= schema["maximum"] and isinstance(example, int)


def test_build_example_from_schema_integer_exclusive_minimum():
    schema = {
        "type": "integer",
        "minimum": 4,
        "exclusiveMinimum": True,
    }
    example = build_example_from_schema(schema)
    assert example > schema["minimum"] and isinstance(example, int)


def test_build_example_from_schema_integer_exclusive_maximum():
    schema = {
        "type": "integer",
        "maximum": 17,
        "exclusiveMaximum": True,
    }
    example = build_example_from_schema(schema)
    assert example < schema["maximum"] and isinstance(example, int)


def test_build_example_from_schema_string_regular_expression():
    pattern = r"^\d{3}-\d{2}-\d{4}$"
    schema = {
        "type": "string",
        "pattern": pattern,
    }
    example = build_example_from_schema(schema)
    assert fullmatch(pattern, example) != None and isinstance(example, str)


def test_build_example_from_schema_string_maximum():
    schema = {
        "type": "string",
        "maxLength": 20,
    }
    example = build_example_from_schema(schema)
    assert isinstance(example, str) and len(example) <= schema["maxLength"]


def test_build_example_from_schema_string_minimum():
    schema = {
        "type": "string",
        "minLength": 20,
    }
    example = build_example_from_schema(schema)
    assert isinstance(example, str) and len(example) >= schema["minLength"]


def test_build_example_from_schema_enum():
    schema = {"type": "string", "enum": ["asc", "desc"]}
    example = build_example_from_schema(schema)
    assert isinstance(example, str)
    assert example == "asc" or example == "desc"


def test_build_example_from_complex_schema():
    schema = {
        "type": "object",
        "properties": {
            "datetimeField": {"type": "string", "format": "date-time"},
            "integerField": {
                "type": "integer",
                "minimum": 2,
                "maximum": 5,
                "exclusiveMinimum": True,
                "multipleOf": 2,
            },
            "arrayOfNumbersField": {
                "type": "array",
                "items": {
                    "type": "number",
                    "format": "float",
                    "minimum": 0.1,
                    "maximum": 0.9,
                    "multipleOf": 0.1,
                },
                "minItems": 3,
                "maxItems": 5,
            },
            "objectField": {
                "type": "object",
                "properties": {
                    "nestedBoolean": {"type": "boolean"},
                    "stringWithExample": {
                        "type": "string",
                        "example": "example-string",
                    },
                },
            },
        },
    }
    example = build_example_from_schema(schema)

    # Check that ValueError is not raised on invalid datetime.
    datetime.fromisoformat(example["datetimeField"])
    assert example["integerField"] == 4

    assert isinstance(example["arrayOfNumbersField"], list)
    assert 3 <= len(example["arrayOfNumbersField"]) <= 5
    assert all(0.1 <= num <= 0.9 for num in example["arrayOfNumbersField"])

    example_boolean = example["objectField"]["nestedBoolean"]
    assert example_boolean is True or example_boolean is False

    # Check that if an example is provided then it is used directly.
    assert example["objectField"]["stringWithExample"] == "example-string"
