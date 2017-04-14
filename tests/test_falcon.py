import pytest
from connexion.apps.falcon_app import FalconApp
from falcon import testing

import conftest

@pytest.fixture()
def client(simple_api_spec_dir):
    app = FalconApp(__name__, specification_dir=simple_api_spec_dir)
    app.add_api('swagger.yaml')
    return testing.TestClient(app.app)


def test_swagger_json(client):
    result = client.simulate_get('/v1.0/swagger.json')
    assert result.status_code == 200
    assert result.json['basePath'] == '/v1.0'


def test_simple(client):
    result = client.simulate_get('/')
    assert result.status_code == 404

    result = client.simulate_get('/v1.0/greeting/hjacobs')
    assert result.status_code == 405

    result = client.simulate_post('/v1.0/greeting/hjacobs')
    assert result.status_code == 200
    assert result.json == {'greeting': 'Hello hjacobs'}


def test_multiple_methods(client):
    result = client.simulate_put('/v1.0/nullable-parameters', body='{"name": "putbody"}')
    assert result.status_code == 200
    assert result.json == {'name': 'putbody'}

    result = client.simulate_get('/v1.0/nullable-parameters', params={'time_start': 123})
    assert result.status_code == 200
    assert result.json == 123


def test_status_code(client):
    result = client.simulate_post('/v1.0/goodday/noheader')
    assert result.status_code == 201
    assert result.json == {'greeting': 'Hello.'}


def test_status_code_headers(client):
    result = client.simulate_post('/v1.0/goodevening/John')
    assert result.status_code == 201
    assert result.text == 'Good evening John'
    assert result.headers['Location'] == '/my/uri'

