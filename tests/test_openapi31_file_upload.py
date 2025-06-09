"""
Tests for file uploads with allOf schema in OpenAPI 3.1
"""

import io
import pathlib

import pytest
from starlette.testclient import TestClient

from connexion import App

TEST_FOLDER = pathlib.Path(__file__).parent


def test_file_upload_simple():
    """Test that simple file uploads work in OpenAPI 3.1."""
    app = App(__name__)
    app.add_api(TEST_FOLDER / "fixtures/openapi_3_1/file_upload_allof.yaml")
    client = TestClient(app)

    # Simple file upload
    files = {
        "file": ("test.txt", b"test content", "text/plain"),
    }
    data = {
        "name": "test-filename",
    }

    response = client.post("/upload/simple", files=files, data=data)
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == len(b"test content")
    assert data["content_type"] == "text/plain"
    assert data["name"] == "test-filename"


def test_file_upload_with_allof():
    """Test that file uploads with allOf schema work in OpenAPI 3.1."""
    app = App(__name__)
    app.add_api(TEST_FOLDER / "fixtures/openapi_3_1/file_upload_allof.yaml")
    client = TestClient(app)

    # File upload with allOf schema
    files = {
        "file": ("test.txt", b"test content", "text/plain"),
    }
    data = {
        "name": "test-filename",
    }

    response = client.post("/upload/with-allof", files=files, data=data)
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == len(b"test content")
    assert data["content_type"] == "text/plain"
    assert data["name"] == "test-filename"
