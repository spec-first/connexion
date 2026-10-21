import pytest
from connexion.resolver import Resolver

from conftest import OPENAPI3_SPEC


@pytest.fixture
def header_client(app_class, spec):
    def build(schema, value, validate_responses=True, **header_options):
        def handler():
            headers = {} if value is None else {"x-test-value": value}
            return {}, 200, headers

        header = {"schema": schema} if spec == OPENAPI3_SPEC else dict(schema)
        header.update(header_options)
        response = {"description": "Success", "headers": {"X-Test-Value": header}}
        operation = {"operationId": "handler", "responses": {"200": response}}
        definition = {
            "info": {"title": "Response headers", "version": "1.0"},
            "paths": {"/headers": {"get": operation}},
        }
        if spec == OPENAPI3_SPEC:
            definition["openapi"] = "3.0.0"
            response["content"] = {"application/json": {"schema": {"type": "object"}}}
        else:
            definition["swagger"] = "2.0"
            definition["produces"] = ["application/json"]
            response["schema"] = {"type": "object"}
        app = app_class(__name__)
        app.add_api(
            definition,
            resolver=Resolver(lambda _: handler),
            validate_responses=validate_responses,
        )
        return app.test_client()

    return build


@pytest.mark.parametrize(
    "schema,value,reason",
    [
        ({"type": "integer"}, "invalid", "integer"),
        ({"type": "integer"}, "1.5", "integer"),
        ({"type": "integer", "minimum": 0}, "-1", "minimum"),
        ({"type": "number", "maximum": 2}, "2.5", "maximum"),
        ({"type": "number"}, "invalid", "number"),
        ({"type": "boolean"}, "invalid", "boolean"),
        ({"type": "string", "enum": ["A", "B"]}, "C", "not one of"),
        ({"type": "string", "minLength": 5}, "abc", "too short"),
        ({"type": "string", "maxLength": 2}, "abc", "too long"),
        ({"type": "string", "pattern": "^[A-Z]+$"}, "abc", "does not match"),
        ({"type": "integer", "enum": [1, 2]}, "3", "not one of"),
    ],
)
def test_invalid_response_header(header_client, schema, value, reason):
    with header_client(schema, value) as client:
        response = client.get("/headers")
    assert response.status_code == 500
    assert "X-Test-Value" in response.json()["detail"]
    assert reason in response.json()["detail"]


@pytest.mark.parametrize(
    "schema,value",
    [
        ({"type": "integer", "minimum": 0}, "42"),
        ({"type": "number", "maximum": 2}, "1.5"),
        ({"type": "boolean"}, "true"),
        ({"type": "boolean"}, "false"),
        ({"type": "string", "enum": ["A", "B"]}, "A"),
        ({"type": "integer", "enum": [1, 2]}, "2"),
        ({"type": "string", "minLength": 0}, ""),
        ({"type": "string", "pattern": "^[A-Z]+$"}, "ABC"),
        ({"type": "integer"}, None),
        ({"type": "array", "items": {"type": "integer"}}, "1,2"),
    ],
)
def test_valid_response_header(header_client, schema, value):
    with header_client(schema, value) as client:
        response = client.get("/headers")
    assert response.status_code == 200
    assert response.headers.get("X-Test-Value") == value


def test_response_header_validation_disabled(header_client):
    with header_client({"type": "integer"}, "invalid", False) as client:
        response = client.get("/headers")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "collection_format,delimiter",
    [("csv", ","), ("ssv", " "), ("tsv", "\t"), ("pipes", "|")],
)
def test_response_header_collection_format(
    header_client, spec, collection_format, delimiter
):
    if spec == OPENAPI3_SPEC:
        pytest.skip("collectionFormat is a Swagger 2 option")
    schema = {"type": "array", "items": {"type": "integer"}, "minItems": 2}
    with header_client(
        schema, delimiter.join(["1", "2"]), collectionFormat=collection_format
    ) as client:
        response = client.get("/headers")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "explode,value", [(False, "count,42,enabled,true"), (True, "count=42,enabled=true")]
)
def test_response_header_object(header_client, spec, explode, value):
    if spec != OPENAPI3_SPEC:
        pytest.skip("Object headers require OpenAPI 3")
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}, "enabled": {"type": "boolean"}},
        "required": ["count", "enabled"],
    }
    with header_client(schema, value, explode=explode) as client:
        response = client.get("/headers")
    assert response.status_code == 200


@pytest.mark.parametrize("value", ["1,invalid", "-1,2"])
def test_response_header_invalid_array(header_client, value):
    schema = {"type": "array", "items": {"type": "integer", "minimum": 0}}
    with header_client(schema, value) as client:
        response = client.get("/headers")
    assert response.status_code == 500
    assert "X-Test-Value" in response.json()["detail"]


@pytest.mark.parametrize("schema_type", ["integer", "array", "object"])
def test_response_header_nullable(header_client, spec, schema_type):
    schema = {"type": schema_type}
    if schema_type == "array":
        schema["items"] = {"type": "integer"}
    if spec == OPENAPI3_SPEC:
        schema["nullable"] = True
    else:
        if schema_type == "object":
            pytest.skip("Object headers require OpenAPI 3")
        schema["x-nullable"] = True
    with header_client(schema, "null") as client:
        response = client.get("/headers")
    assert response.status_code == 200
    assert response.headers["X-Test-Value"] == "null"


@pytest.mark.parametrize(
    "explode,value",
    [
        (False, "count"),
        (True, "count"),
        (False, "count,invalid"),
        (True, "count=invalid"),
    ],
)
def test_response_header_invalid_object(header_client, spec, explode, value):
    if spec != OPENAPI3_SPEC:
        pytest.skip("Object headers require OpenAPI 3")
    schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
    with header_client(schema, value, explode=explode) as client:
        response = client.get("/headers")
    assert response.status_code == 500
    assert "X-Test-Value" in response.json()["detail"]


def test_response_header_required(header_client, spec):
    if spec != OPENAPI3_SPEC:
        pytest.skip("required is an OpenAPI 3 header field")
    with header_client({"type": "integer"}, None, required=True) as client:
        response = client.get("/headers")
    assert response.status_code == 500
    assert "x-test-value" in response.json()["detail"]
