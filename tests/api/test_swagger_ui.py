def test_simple(swagger_ui_app):
    app_client = swagger_ui_app.test_client()
    response = app_client.get("/v1.0/spec.json")
    assert response.status_code == 200
