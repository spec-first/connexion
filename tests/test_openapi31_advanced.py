"""
Tests for advanced OpenAPI 3.1 features in Connexion
"""

import json
import pathlib
import pytest

from connexion import FlaskApp
from connexion.exceptions import InvalidSpecification
from connexion.json_schema import Draft2020RequestValidator, Draft2020ResponseValidator
from connexion.spec import OpenAPI31Specification
from jsonschema import Draft202012Validator

TEST_FOLDER = pathlib.Path(__file__).parent


def test_openapi31_type_arrays():
    """Test that type arrays work for schema validation in OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(TEST_FOLDER / 'fixtures/openapi_3_1/advanced_openapi.yaml', base_path="/v1")
    client = app.test_client()
    
    # Test with nullable name (should pass)
    response = client.post('/v1/advanced-pets', 
                         json={"id": 10, "name": None, "species": "cat", "age": 2})
    assert response.status_code == 201
    
    # Test without name (should pass since it's not required)
    response = client.post('/v1/advanced-pets', 
                         json={"id": 11, "species": "dog", "age": 3})
    assert response.status_code == 201
    
    # Test with name as incorrect type (not string or null)
    response = client.post('/v1/advanced-pets', 
                         json={"id": 12, "name": 123, "species": "bird", "age": 1})
    assert response.status_code == 400
    
    # Test GET endpoint to verify nullable fields are returned properly
    response = client.get('/v1/advanced-pets')
    assert response.status_code == 200
    pets = json.loads(response.text)
    
    # Find the bird pet with null name
    bird_pet = next((pet for pet in pets if pet["species"] == "bird"), None)
    assert bird_pet is not None
    assert bird_pet["name"] is None


def test_openapi31_exclusiveminimum():
    """Test direct exclusiveMinimum handling in OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(TEST_FOLDER / 'fixtures/openapi_3_1/advanced_openapi.yaml', base_path="/v1")
    client = app.test_client()
    
    # Test with valid age (positive)
    response = client.post('/v1/advanced-pets', 
                         json={"id": 20, "species": "cat", "age": 2})
    assert response.status_code == 201
    
    # Test with invalid age (zero)
    response = client.post('/v1/advanced-pets', 
                         json={"id": 21, "species": "dog", "age": 0})
    assert response.status_code == 400
    
    # Test with invalid age (negative)
    response = client.post('/v1/advanced-pets', 
                         json={"id": 22, "species": "bird", "age": -1})
    assert response.status_code == 400


def test_openapi31_unevaluated_properties():
    """Test unevaluatedProperties in OpenAPI 3.1."""
    app = FlaskApp(__name__)
    app.add_api(TEST_FOLDER / 'fixtures/openapi_3_1/advanced_openapi.yaml', base_path="/v1")
    client = app.test_client()
    
    # Test with valid metadata
    response = client.post('/v1/advanced-pets/with-metadata', 
                         json={"id": 30, "species": "cat", "metadata": {"color": "black", "weight": 4.5}})
    assert response.status_code == 201
    
    # Test with invalid metadata (unknown property)
    response = client.post('/v1/advanced-pets/with-metadata', 
                         json={"id": 31, "species": "dog", "metadata": {"color": "brown", "unknown": "value"}})
    assert response.status_code == 400


def test_openapi31_server_variables():
    """Test server variables and templating in OpenAPI 3.1."""
    from connexion.spec import Specification
    
    spec_path = TEST_FOLDER / 'fixtures/openapi_3_1/advanced_openapi.yaml'
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
            "age": {"type": "number", "exclusiveMinimum": 0}
        },
        "required": ["age"]
    }
    
    # Create our custom Draft2020 validator
    validator = Draft2020RequestValidator(test_schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    
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
    
    spec_path = TEST_FOLDER / 'fixtures/openapi_3_1/advanced_openapi.yaml'
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
    
    spec_path = TEST_FOLDER / 'fixtures/openapi_3_1/advanced_openapi.yaml'
    spec = Specification.load(spec_path)
    
    # Check webhooks are parsed correctly
    assert "webhooks" in spec
    assert "newPet" in spec["webhooks"]
    
    # Check webhook operation details
    webhook = spec["webhooks"]["newPet"]
    assert "post" in webhook
    assert webhook["post"]["operationId"] == "tests.fixtures.openapi_3_1.advanced_api.process_new_pet_webhook"
    
    # Verify response schema
    assert "responses" in webhook["post"]
    assert "200" in webhook["post"]["responses"]