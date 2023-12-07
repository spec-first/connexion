from connexion.middleware.swagger_ui import SwaggerUIConfig


def test_simple(simple_app):
    app_client = simple_app.test_client()
    for api in simple_app.middleware.apis:
        if api.kwargs['swagger_ui_options']:
            swagger_ui_options = api.kwargs['swagger_ui_options']
        else:
            swagger_ui_options = simple_app.middleware.options.swagger_ui_options

        options = SwaggerUIConfig(
            swagger_ui_options, oas_version=api.specification.version
        )
        response = app_client.get(api.specification.base_path+options.openapi_spec_path)
        assert response.status_code == 200


def test_simple_openapi(simple_openapi_app):
    app_client = simple_openapi_app.test_client()
    for api in simple_openapi_app.middleware.apis:
        if api.kwargs['swagger_ui_options']:
            swagger_ui_options = api.kwargs['swagger_ui_options']
        else:
            swagger_ui_options = simple_openapi_app.middleware.options.swagger_ui_options

        options = SwaggerUIConfig(
            swagger_ui_options, oas_version=api.specification.version
        )
        response = app_client.get(api.specification.base_path+options.openapi_spec_path)
        assert response.status_code == 200
