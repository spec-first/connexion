from re import fullmatch

from connexion.utils import generate_example


def test_generate_example_string():

    schema = {
        "type": "string",
    }

    example = generate_example(schema)

    assert isinstance(example, str)


def test_generate_example_integer():

    schema = {
        "type": "integer",
    }

    example = generate_example(schema)

    assert isinstance(example, int)


def test_generate_example_number():

    schema = {
        "type": "number",
    }

    example = generate_example(schema)

    assert isinstance(example, float)


def test_generate_example_boolean():

    schema = {
        "type": "boolean",
    }

    example = generate_example(schema)

    assert isinstance(example, bool)


def test_generate_example_integer_minimum():

    schema = {
        "type": "integer",
        "minimum": 4,
    }

    example = generate_example(schema)

    assert example >= schema["minimum"] and isinstance(example, int)


def test_generate_example_integer_maximum():

    schema = {
        "type": "integer",
        "maximum": 17,
    }

    example = generate_example(schema)

    assert example <= schema["maximum"] and isinstance(example, int)


def test_generate_example_integer_exclusive_minimum():

    schema = {
        "type": "integer",
        "minimum": 4,
        "exclusiveMinimum": True,
    }
    example = generate_example(schema)

    assert example > schema["minimum"] and isinstance(example, int)


def test_generate_example_integer_exclusive_maximum():

    schema = {
        "type": "integer",
        "maximum": 17,
        "exclusiveMaximum": True,
    }

    example = generate_example(schema)

    assert example < schema["maximum"] and isinstance(example, int)


def test_generate_example_string_regular_expression():

    pattern = "^\d{3}-\d{2}-\d{4}$"

    schema = {
        "type": "string",
        "pattern": pattern,
    }

    example = generate_example(schema)

    assert fullmatch(pattern, example) != None and isinstance(example, str)


def test_generate_example_string_maximum():

    schema = {
        "type": "string",
        "maxLength": 20,
    }

    example = generate_example(schema)

    assert isinstance(example, str) and len(example) <= schema["maxLength"]


def test_generate_example_string_minimum():

    schema = {
        "type": "string",
        "minLength": 20,
    }

    example = generate_example(schema)

    assert isinstance(example, str) and len(example) >= schema["minLength"]


def test_generate_example_enum():

    schema = {"type": "string", "enum": ["asc", "desc"]}

    example = generate_example(schema)

    assert isinstance(example, str)
    assert example == "asc" or example == "desc"
