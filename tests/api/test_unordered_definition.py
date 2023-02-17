import json


def test_app(unordered_definition_app):
    app_client = unordered_definition_app.test_client()
    response = app_client.get("/v1.0/unordered-params/1?first=first&second=2")
    assert response.status_code == 400
    response_data = response.json()
    assert response_data["detail"].startswith("'first' is not of type 'integer'")
