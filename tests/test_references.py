from unittest import mock

import pytest
from connexion.json_schema import Draft4RequestValidator, resolve_refs
from connexion.jsonifier import Jsonifier
from referencing.exceptions import Unresolvable

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
    with pytest.raises(Unresolvable) as exc_info:  # type: py.code.ExceptionInfo
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

    with pytest.raises(Unresolvable) as exc_info:  # type: py.code.ExceptionInfo
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

    with pytest.raises(Unresolvable) as exc_info:
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


def test_resolve_nested_ref_inside_inlined_schema(api):
    """References nested inside an inlined schema resolve at the use site."""
    op_spec = {
        "parameters": [
            {
                "schema": {"$ref": "#/definitions/Wrapper"},
            }
        ],
        "definitions": {
            "Wrapper": {
                "type": "object",
                "properties": {"inner": {"$ref": "#/definitions/Inner"}},
            },
            "Inner": {"type": "string"},
        },
    }

    spec = resolve_refs(op_spec)
    assert spec["parameters"][0]["schema"]["properties"]["inner"] == {"type": "string"}


def test_recursive_reference_does_not_create_cycle(api):
    """A schema referencing itself must not become a cyclic object graph.

    Inlining a self-referential schema used to share sub-objects with the
    spec, so the resolved schema contained a cycle: serializing it failed
    and validating a request body against it looped forever. The recursive
    reference is now left in place, to be resolved against the components
    section by the validator (as request/response body schemas already do).
    """
    import json

    op_spec = {
        "paths": {
            "/": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "bar": {"$ref": "#/components/schemas/Bar"}
                                    },
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Bar": {
                    "type": "object",
                    "properties": {"child": {"$ref": "#/components/schemas/Bar"}},
                }
            }
        },
    }

    spec = resolve_refs(op_spec)
    # No cyclic object graph: the resolved spec must serialize.
    json.dumps(spec)
    bar = spec["paths"]["/"]["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["properties"]["bar"]
    assert bar["properties"]["child"] == {"$ref": "#/components/schemas/Bar"}
    # The components definition itself is expanded one level, with the
    # recursion point left as a reference at the second level.
    assert spec["components"]["schemas"]["Bar"]["properties"]["child"] == {
        "type": "object",
        "properties": {"child": {"$ref": "#/components/schemas/Bar"}},
    }

    # And validation against the body schema (with components attached,
    # as OpenAPI operations do) terminates and follows the instance depth.
    body_schema = spec["paths"]["/"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    body_schema["components"] = spec["components"]
    validator = Draft4RequestValidator(body_schema)
    assert list(validator.iter_errors({"bar": {"child": {"child": {}}}})) == []
    errors = list(validator.iter_errors({"bar": {"child": 5}}))
    assert len(errors) == 1
    assert "is not of type 'object'" in errors[0].message
