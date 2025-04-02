"""
Test for file uploads with allOf and $ref in OpenAPI 3.1 (issue #2018)
"""

import pathlib

import pytest
from starlette.testclient import TestClient

from connexion import App

TEST_FOLDER = pathlib.Path(__file__).parent


def test_file_upload_with_allof_ref():
    """Test a file upload with allOf and $ref in OpenAPI 3.1 (issue #2018)"""
    app = App(__name__)
    app.add_api(TEST_FOLDER / 'fixtures/openapi_3_1/file_upload_allof_ref.yaml')
    client = TestClient(app)
    
    # Create a file to upload
    files = {
        'file': ('test.txt', b'test content for allOf $ref', 'text/plain'),
    }
    data = {
        'fileName': 'test-ref-file.txt',
        'description': 'A test file with allOf and $ref',
    }
    
    response = client.post('/upload-with-ref', files=files, data=data)
    
    # Check response
    assert response.status_code == 200
    
    # Verify response data
    response_data = response.json()
    assert response_data['success'] is True
    assert response_data['fileName'] == 'test-ref-file.txt'
    assert response_data['description'] == 'A test file with allOf and $ref'
    assert isinstance(response_data['size'], int)