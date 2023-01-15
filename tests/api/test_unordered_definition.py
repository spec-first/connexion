import json


def test_app(unordered_definition_app):
    app_client = unordered_definition_app.test_client()
    response = app_client.get(
        "/v1.0/unordered-params/1?first=first&second=2"
    )  # type: flask.Response
    assert response.status_code == 400
    response_data = json.loads(response.data.decode("utf-8", "replace"))
    assert (
        response_data["detail"]
        == "Wrong type, expected 'integer' for query parameter 'first'"
    )
