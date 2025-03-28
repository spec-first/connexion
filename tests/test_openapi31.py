"""
Tests for OpenAPI 3.1 support in Connexion
"""

import json
import pathlib

import pytest
from connexion import FlaskApp
from connexion.exceptions import InvalidSpecification
from connexion.spec import OpenAPI31Specification

TEST_FOLDER = pathlib.Path(__file__).parent


def test_openapi31_loading():
    """Test that Connexion can load an OpenAPI 3.1 specification."""
    # We directly test the OpenAPI31Specification class instead of using the app
    from connexion.spec import Specification

    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/openapi.yaml"
    spec = Specification.load(spec_path)

    assert spec.version == (3, 1, 0)
    assert isinstance(spec, OpenAPI31Specification)
    assert spec.json_schema_dialect == "https://json-schema.org/draft/2020-12/schema"


def test_openapi31_validation():
    """Test that Connexion can validate requests and responses with OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(TEST_FOLDER / "fixtures/openapi_3_1/openapi.yaml")
    client = app.test_client()

    # Test GET /pets
    response = client.get("/pets")
    assert response.status_code == 200
    assert json.loads(response.text) == [
        {"id": 1, "name": "Fluffy", "tag": "cat"},
        {"id": 2, "name": "Buddy", "tag": "dog"},
    ]

    # Test GET /pets/{pet_id}
    response = client.get("/pets/1")
    assert response.status_code == 200
    assert json.loads(response.text) == {"id": 1, "name": "Fluffy", "tag": "cat"}

    # Test GET /pets/{pet_id} with non-existent ID
    response = client.get("/pets/999")
    assert response.status_code == 404

    # Test POST /pets with valid data
    response = client.post("/pets", json={"id": 3, "name": "Rex", "tag": "dog"})
    assert response.status_code == 201
    assert json.loads(response.text) == {"id": 3, "name": "Rex", "tag": "dog"}

    # Test POST /pets with invalid data (missing required field)
    response = client.post("/pets", json={"id": 4})
    assert response.status_code == 400


def test_openapi31_missing_schema_dialect():
    """Test that Connexion uses the default schema dialect if not specified."""
    # We directly test the OpenAPI31Specification class instead of using the app
    from connexion.spec import Specification

    # Remove the jsonSchemaDialect field from the YAML
    with open(TEST_FOLDER / "fixtures/openapi_3_1/openapi.yaml", "r") as f:
        spec_text = f.read()

    spec_text = spec_text.replace(
        "jsonSchemaDialect: https://json-schema.org/draft/2020-12/schema\n", ""
    )

    with open(TEST_FOLDER / "fixtures/openapi_3_1/openapi_no_dialect.yaml", "w") as f:
        f.write(spec_text)

    spec_path = TEST_FOLDER / "fixtures/openapi_3_1/openapi_no_dialect.yaml"
    spec = Specification.load(spec_path)

    assert spec.json_schema_dialect == "https://json-schema.org/draft/2020-12/schema"


def test_openapi31_invalid_version():
    """Test that Connexion rejects an invalid OpenAPI version."""
    app = FlaskApp(__name__)

    # Create an OpenAPI spec with invalid version
    with open(TEST_FOLDER / "fixtures/openapi_3_1/openapi.yaml", "r") as f:
        spec_text = f.read()

    spec_text = spec_text.replace("openapi: 3.1.0", "openapi: 3.2.0")

    with open(TEST_FOLDER / "fixtures/openapi_3_1/openapi_invalid.yaml", "w") as f:
        f.write(spec_text)

    # Test that it raises an exception
    with pytest.raises(InvalidSpecification):
        app.add_api(TEST_FOLDER / "fixtures/openapi_3_1/openapi_invalid.yaml")
