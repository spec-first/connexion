import sys

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
    [],
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


@pytest.mark.skipif(sys.version_info < (3, 4),
                    reason="requires python3.4 or higher")
def test_validate_operation_output_enum():
    """Support enum status, see #504."""
    from enum import Enum

    class HTTPStatus(Enum):
        OK = 200

    output = ("test", HTTPStatus.OK)
    _, status, _ = validate_operation_output(output)
    assert isinstance(status, int) and status == 200


@pytest.mark.skipif(sys.version_info < (3, 5),
                    reason="requires python3.5 or higher")
def test_validate_operation_output_httpstatus():
    """Support http.HTTPStatus, see #504."""
    from http import HTTPStatus

    output = ("test", HTTPStatus.OK)
    _, status, _ = validate_operation_output(output)
    assert isinstance(status, int) and status == 200
