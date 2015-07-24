import pytest

from connexion.decorators.validation import validate_pattern, validate_minimum, validate_maximum

def test_validate_pattern():
    assert validate_pattern({}, '') is None
    assert validate_pattern({'pattern': 'a'}, 'a') is None
    assert validate_pattern({'pattern': 'a'}, 'b') == 'Invalid value, pattern "a" does not match'


def test_validate_minimum():
    assert validate_minimum({}, 1) is None
    assert validate_minimum({'minimum': 1}, 1) is None
    assert validate_minimum({'minimum': 1.1}, 1) == 'Invalid value, must be at least 1.1'


def test_validate_maximum():
    assert validate_maximum({}, 1) is None
    assert validate_maximum({'maximum': 1}, 1) is None
    assert validate_maximum({'maximum': 0}, 1) == 'Invalid value, must be at most 0'
