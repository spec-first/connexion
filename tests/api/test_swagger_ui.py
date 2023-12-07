
def test_simple(swagger_app):
    app_client = swagger_app.test_client()
    for api in swagger_app.middleware.apis:
        response = app_client.get(api.specification.base_path+"/spec.json")
        assert response.status_code == 200
