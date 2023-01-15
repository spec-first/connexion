from unittest import mock

import pytest
from connexion.json_schema import RefResolutionError, resolve_refs
from connexion.jsonifier import Jsonifier

DEFINITIONS = {
    "new_stack": {
        "required": ["image_version", "keep_stacks", "new_traffic", "senza_yaml"],
        "type": "object",
        "properties": {
            "keep_stacks": {
                "type": "integer",
                "description": "Number of older stacks to keep",
            },
            "image_version": {
                "type": "string",
                "description": "Docker image version to deploy",
            },
            "senza_yaml": {"type": "string", "description": "YAML to provide to senza"},
            "new_traffic": {
                "type": "integer",
                "description": "Percentage of the traffic",
            },
        },
    },
    "composed": {
        "required": ["test"],
        "type": "object",
        "properties": {"test": {"schema": {"$ref": "#/definitions/new_stack"}}},
    },
    "problem": {"some": "thing"},
}
PARAMETER_DEFINITIONS = {"myparam": {"in": "path", "type": "integer"}}


@pytest.fixture
def api():
    return mock.MagicMock(jsonifier=Jsonifier)


def test_non_existent_reference(api):
    op_spec = {
        "parameters": [
            {
                "in": "body",
                "name": "new_stack",
                "required": True,
                "schema": {"$ref": "#/definitions/new_stack"},
            }
        ]
    }
    with pytest.raises(RefResolutionError) as exc_info:  # type: py.code.ExceptionInfo
        resolve_refs(op_spec, {})

    exception = exc_info.value
    assert "definitions/new_stack" in str(exception)


def test_invalid_reference(api):
    op_spec = {
        "parameters": [
            {
                "in": "body",
                "name": "new_stack",
                "required": True,
                "schema": {"$ref": "#/notdefinitions/new_stack"},
            }
        ]
    }

    with pytest.raises(RefResolutionError) as exc_info:  # type: py.code.ExceptionInfo
        resolve_refs(
            op_spec, {"definitions": DEFINITIONS, "parameters": PARAMETER_DEFINITIONS}
        )

    exception = exc_info.value
    assert "notdefinitions/new_stack" in str(exception)


def test_resolve_invalid_reference(api):
    op_spec = {
        "operationId": "fakeapi.hello.post_greeting",
        "parameters": [{"$ref": "/parameters/fail"}],
    }

    with pytest.raises(RefResolutionError) as exc_info:
        resolve_refs(op_spec, {"parameters": PARAMETER_DEFINITIONS})

    exception = exc_info.value
    assert "parameters/fail" in str(exception)


def test_resolve_web_reference(api):
    op_spec = {"parameters": [{"$ref": "https://reallyfake.asd/parameters.json"}]}
    store = {"https://reallyfake.asd/parameters.json": {"name": "test"}}

    spec = resolve_refs(op_spec, store=store)
    assert spec["parameters"][0]["name"] == "test"


def test_resolve_ref_referring_to_another_ref(api):
    expected = {"type": "string"}
    op_spec = {
        "parameters": [
            {
                "schema": {"$ref": "#/definitions/A"},
            }
        ],
        "definitions": {
            "A": {
                "$ref": "#/definitions/B",
            },
            "B": expected,
        },
    }

    spec = resolve_refs(op_spec)
    assert spec["parameters"][0]["schema"] == expected
    assert spec["definitions"]["A"] == expected
