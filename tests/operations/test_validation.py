import pytest

from connexion.operations.validation import (
    BODY_TYPES,
    validate_operation_output
)


@pytest.mark.parametrize("output", [
    ("test", 200, {}),
    "test",
    b"test",
    ("test",),
    {},
    []
])
def test_validate_operation_output(output):
    body, status, headers = validate_operation_output(output)
    assert isinstance(body, BODY_TYPES)
    assert isinstance(status, int) or status is None
    assert isinstance(headers, dict) or headers is None
