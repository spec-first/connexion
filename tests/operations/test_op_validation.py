import pytest
from connexion.decorators.produces import NoContent
from connexion.operations.validation import (BODY_TYPES,
                                             validate_operation_output)


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


@pytest.mark.parametrize("output", [
    NoContent,
    (NoContent,)
])
def test_validate_operation_no_content(output):
    body, _, _ = validate_operation_output(output)
    assert body == b""
