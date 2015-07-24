import pytest

from connexion.decorators.validation import validate_pattern

def test_validate_pattern():
    assert validate_pattern({}, '') is None
    assert validate_pattern({'pattern': 'a'}, 'a') is None
    assert validate_pattern({'pattern': 'a'}, 'b') == 'Invalid value, pattern "a" does not match'

