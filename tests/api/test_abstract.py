import json

import pytest
from connexion.apis import AbstractAPI
from connexion.utils import Jsonifier


@pytest.mark.parametrize("body,mimetype,expected", [
    (None, None, b"null\n"),
    # is returned as it is with mimetype text/plain
    ("test", "text/plain", b"test"),
    (b"test", "text/plain", b"test"),
    ("test", "application/json", b'"test"\n'),
    (b"test", "application/json", b'"test"\n'),
])
def test_encode_body(body, mimetype, expected):
    """Test the body encoding.

    Jsonifier adds a `\n` after the serialized string.
    """
    assert AbstractAPI.encode_body(body, mimetype) == expected


@pytest.mark.parametrize("body", [
    None,
    {"test": 1},
    ["test"],
])
def test_encode_body_objects(body):
    encoded = AbstractAPI.encode_body(body, mimetype="application/json")
    serde = Jsonifier(json)
    assert encoded == serde.dumps(body).encode("UTF-8")
    assert encoded.decode("UTF-8")[-1] == "\n"
    assert serde.loads(encoded) == body
