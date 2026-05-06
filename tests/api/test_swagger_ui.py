from connexion.spec import Specification


def test_simple(swagger_ui_app):
    app_client = swagger_ui_app.test_client()
    response = app_client.get("/v1.0/spec.json")
    assert response.status_code == 200
    # Load the spec into Connexion to validate it
    Specification.from_dict(response.json())


def test_basepath(swagger_ui_basepath_app):
    app_client = swagger_ui_basepath_app.test_client()
    response = app_client.get("/spec.json")
    assert response.status_code == 200
    # Load the spec into Connexion to validate it
    Specification.from_dict(response.json())
