import json

def test_cors_valid(cors_openapi_app):
    app_client = cors_openapi_app.test_client()
    response = app_client.post(
        "/v1.0/goodday/dan", data={}, headers={"Origin": "http://localhost"}
    )
    assert response.status_code == 201
    assert "Access-Control-Allow-Origin" in response.headers


def test_cors_invalid(cors_openapi_app):
    app_client = cors_openapi_app.test_client()
    response = app_client.options(
        "/v1.0/goodday/dan", headers={"Origin": "http://0.0.0.0"}
    )
    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_validation_error(cors_openapi_app):
    app_client = cors_openapi_app.test_client()
    response = app_client.post(
        "/v1.0/body-not-allowed-additional-properties",
        data={},
        headers={"Origin": "http://localhost"},
    )
    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" in response.headers


def test_cors_server_error(cors_openapi_app):
    app_client = cors_openapi_app.test_client()
    response = app_client.post(
        "/v1.0/goodday/noheader", data={}, headers={"Origin": "http://localhost"}
    )
    assert response.status_code == 500

    assert "Access-Control-Allow-Origin" in response.headers
