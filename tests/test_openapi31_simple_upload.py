"""
Test for basic file upload in OpenAPI 3.1
"""

import pathlib

import pytest
from starlette.testclient import TestClient

from connexion import App

TEST_FOLDER = pathlib.Path(__file__).parent


def test_simple_file_upload():
    """Test a basic file upload with OpenAPI 3.1"""
    app = App(__name__)
    app.add_api(TEST_FOLDER / 'fixtures/openapi_3_1/file_upload.yaml')
    client = TestClient(app)
    
    # Create a simple file to upload
    files = {
        'file': ('test.txt', b'test content', 'text/plain'),
    }
    data = {
        'fileName': 'test-file.txt', 
    }
    
    response = client.post('/upload', files=files, data=data)
    
    # Now we know it should work - verify the actual response
    assert response.status_code == 200
    
    # Verify the response data
    response_data = response.json()
    assert response_data['uploaded'] is True
    assert response_data['fileName'] == 'test-file.txt'
    assert response_data['size'] == len(b'test content')