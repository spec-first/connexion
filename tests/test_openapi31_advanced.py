"""
Tests for advanced OpenAPI 3.1 features in Connexion
"""

import json
import pathlib
import pytest
import yaml

from connexion import FlaskApp
from connexion.exceptions import InvalidSpecification
from connexion.json_schema import Draft2020RequestValidator, Draft2020ResponseValidator
from connexion.spec import OpenAPI31Specification, Specification
from jsonschema import Draft202012Validator

TEST_FOLDER = pathlib.Path(__file__).parent


def test_openapi31_type_arrays():
    """Test that type arrays work for schema validation in OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(
        TEST_FOLDER / "fixtures/openapi_3_1/advanced_openapi.yaml", base_path="/v1"
    )
    client = app.test_client()

    # Test with nullable name (should pass)
    response = client.post(
        "/v1/advanced-pets", json={"id": 10, "name": None, "species": "cat", "age": 2}
    )
    assert response.status_code == 201

    # Test without name (should pass since it's not required)
    response = client.post(
        "/v1/advanced-pets", json={"id": 11, "species": "dog", "age": 3}
    )
    assert response.status_code == 201

    # Test with name as incorrect type (not string or null)
    response = client.post(
        "/v1/advanced-pets", json={"id": 12, "name": 123, "species": "bird", "age": 1}
    )
    assert response.status_code == 400

    # Test GET endpoint to verify nullable fields are returned properly
    response = client.get("/v1/advanced-pets")
    assert response.status_code == 200
    pets = json.loads(response.text)

    # Find the bird pet with null name
    bird_pet = next((pet for pet in pets if pet["species"] == "bird"), None)
    assert bird_pet is not None
    assert bird_pet["name"] is None


def test_openapi31_exclusiveminimum():
    """Test direct exclusiveMinimum handling in OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(
        TEST_FOLDER / "fixtures/openapi_3_1/advanced_openapi.yaml", base_path="/v1"
    )
    client = app.test_client()

    # Test with valid age (positive)
    response = client.post(
        "/v1/advanced-pets", json={"id": 20, "species": "cat", "age": 2}
    )
    assert response.status_code == 201

    # Test with invalid age (zero)
    response = client.post(
        "/v1/advanced-pets", json={"id": 21, "species": "dog", "age": 0}
    )
    assert response.status_code == 400

    # Test with invalid age (negative)
    response = client.post(
        "/v1/advanced-pets", json={"id": 22, "species": "bird", "age": -1}
    )
    assert response.status_code == 400


def test_openapi31_unevaluated_properties():
    """Test unevaluatedProperties in OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(
        TEST_FOLDER / "fixtures/openapi_3_1/advanced_openapi.yaml", base_path="/v1"
    )
    client = app.test_client()

    # Test with valid metadata
    response = client.post(
        "/v1/advanced-pets/with-metadata",
        json={
            "id": 30,
            "species": "cat",
            "metadata": {"color": "black", "weight": 4.5},
        },
    )
    assert response.status_code == 201

    # Test with invalid metadata (unknown property)
    response = client.post(
        "/v1/advanced-pets/with-metadata",
        json={
            "id": 31,
            "species": "dog",
            "metadata": {"color": "brown", "unknown": "value"},
        },
    )
    assert response.status_code == 400


def test_openapi31_server_variables():
    """Test server variables and templating in OpenAPI 3.1."""
    from connexion.spec import Specification

    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/advanced_openapi.yaml"
    spec = Specification.load(spec_path)

    # Check server URL template
    assert spec["servers"][0]["url"] == "https://{environment}.example.com/v1"

    # Check server variables
    variables = spec["servers"][0]["variables"]
    assert variables["environment"]["default"] == "api"
    assert "api" in variables["environment"]["enum"]
    assert "staging" in variables["environment"]["enum"]
    assert "dev" in variables["environment"]["enum"]


def test_openapi31_json_schema_validation():
    """Test the Draft202012Validator is properly used for OpenAPI 3.1."""
    # Create a test schema to validate
    test_schema = {
        "type": "object",
        "properties": {
            "name": {"type": ["string", "null"]},
            "age": {"type": "number", "exclusiveMinimum": 0},
        },
        "required": ["age"],
    }

    # Create our custom Draft2020 validator
    validator = Draft2020RequestValidator(
        test_schema, format_checker=Draft202012Validator.FORMAT_CHECKER
    )

    # Test valid cases
    validator.validate({"name": "test", "age": 10})
    validator.validate({"name": None, "age": 10})
    validator.validate({"age": 10})

    # Test invalid cases
    with pytest.raises(Exception):
        validator.validate({"name": "test"})  # Missing required age

    with pytest.raises(Exception):
        validator.validate({"name": 123, "age": 10})  # Name is not string or null

    with pytest.raises(Exception):
        validator.validate({"name": "test", "age": 0})  # Age not greater than 0

    with pytest.raises(Exception):
        validator.validate({"name": "test", "age": -1})  # Age negative


def test_openapi31_examples():
    """Test examples functionality in OpenAPI 3.1."""
    from connexion.spec import Specification

    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/advanced_openapi.yaml"
    spec = Specification.load(spec_path)

    # Verify the example exists
    assert "examples" in spec["components"]
    assert "PetExample" in spec["components"]["examples"]

    # Check the example content
    example = spec["components"]["examples"]["PetExample"]
    assert example["summary"] == "Example of a valid pet"
    assert example["value"]["id"] == 1
    assert example["value"]["name"] == "Fluffy"
    assert example["value"]["species"] == "cat"
    assert example["value"]["age"] == 3


def test_openapi31_webhooks():
    """Test webhook definition parsing in OpenAPI 3.1."""
    from connexion.spec import Specification

    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/advanced_openapi.yaml"
    spec = Specification.load(spec_path)

    # Check webhooks are parsed correctly
    assert "webhooks" in spec
    assert "newPet" in spec["webhooks"]

    # Check webhook operation details
    webhook = spec["webhooks"]["newPet"]
    assert "post" in webhook
    assert (
        webhook["post"]["operationId"]
        == "tests.fixtures.openapi_3_1.advanced_api.process_new_pet_webhook"
    )

    # Verify response schema
    assert "responses" in webhook["post"]
    assert "200" in webhook["post"]["responses"]


def test_openapi31_minimal_document():
    """Test that OpenAPI 3.1 documents without paths are valid."""
    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/minimal_openapi.yaml"
    spec = Specification.load(spec_path)

    # Verify it's a valid OpenAPI 3.1 document
    assert spec.version == (3, 1, 0)
    assert isinstance(spec, OpenAPI31Specification)

    # Verify the minimal structure
    assert "info" in spec
    assert spec["info"]["title"] == "Minimal OpenAPI 3.1 Document"
    assert (
        spec["info"]["summary"] == "A minimal valid OpenAPI 3.1 document without paths"
    )

    # Verify there are no paths
    assert "paths" not in spec or not spec["paths"]

    # Verify components exist
    assert "components" in spec
    assert "schemas" in spec["components"]
    assert "Pet" in spec["components"]["schemas"]


def test_openapi31_path_items_in_components():
    """Test pathItems in Components for OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(
        TEST_FOLDER / "fixtures/openapi_3_1/path_items_components.yaml", base_path="/v1"
    )
    client = app.test_client()

    # Test that paths using references to pathItems components work
    response = client.get("/v1/pets")
    assert response.status_code == 200

    # Verify the POST operation works too
    response = client.post(
        "/v1/pets", json={"id": 40, "species": "cat", "name": "Felix"}
    )
    assert response.status_code == 201

    # Now check the raw spec directly to confirm pathItems exist in components
    # We use spec.raw to get the unresolved spec
    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/path_items_components.yaml"
    spec = Specification.load(spec_path)

    with open(spec_path, "r") as f:
        raw_spec = yaml.safe_load(f)

    # Verify path reference in raw spec
    assert "/pets" in raw_spec["paths"]
    assert "$ref" in raw_spec["paths"]["/pets"]
    assert raw_spec["paths"]["/pets"]["$ref"] == "#/components/pathItems/PetsPathItem"

    # Verify pathItems in components
    assert "pathItems" in raw_spec["components"]
    assert "PetsPathItem" in raw_spec["components"]["pathItems"]
    assert "get" in raw_spec["components"]["pathItems"]["PetsPathItem"]
    assert "post" in raw_spec["components"]["pathItems"]["PetsPathItem"]

    # Verify the property is accessible via our API
    assert "pathItems" in spec.components
    assert hasattr(spec, "path_items")
    assert "PetsPathItem" in spec.path_items


def test_openapi31_security_improvements():
    """Test security improvements in OpenAPI 3.1."""
    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/security_improvements.yaml"
    spec = Specification.load(spec_path)

    # Verify security schemes
    assert "securitySchemes" in spec["components"]

    # Verify OAuth2 with scopes
    assert "OAuth2" in spec["components"]["securitySchemes"]
    assert spec["components"]["securitySchemes"]["OAuth2"]["type"] == "oauth2"

    # Verify mutualTLS security scheme
    assert "mutualTLS" in spec["components"]["securitySchemes"]
    assert spec["components"]["securitySchemes"]["mutualTLS"]["type"] == "mutualTLS"

    # Verify security requirements with scopes array
    security = spec["paths"]["/secure"]["get"]["security"]
    oauth_security = next(item for item in security if "OAuth2" in item)
    assert "read:pets" in oauth_security["OAuth2"]
    assert "write:pets" in oauth_security["OAuth2"]
