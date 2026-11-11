"""
fixtures available for injection to tests by pytest
"""
import pytest
from app import conn_app
from starlette.testclient import TestClient


@pytest.fixture
def client():
    """
    Create a Connexion test_client from the Connexion app.

    https://connexion.readthedocs.io/en/stable/testing.html
    """
    client: TestClient = conn_app.test_client()
    yield client
