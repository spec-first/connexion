import json
from struct import unpack

import yaml
from connexion import FlaskApp
from connexion.frameworks.flask import FlaskJSONProvider

from conftest import build_app_from_fixture


def test_app(simple_app):
    app_client = simple_app.test_client()

    # by default the Swagger UI is enabled
    swagger_ui = app_client.get("/v1.0/ui/")
    assert swagger_ui.status_code == 200
    assert "Swagger UI" in swagger_ui.text

    # test return Swagger UI static files
    swagger_icon = app_client.get("/v1.0/ui/swagger-ui.js")
    assert swagger_icon.status_code == 200

    post_greeting_url = app_client.post(
        "/v1.0/greeting/jsantos/the/third/of/his/name", data={}
    )
    assert post_greeting_url.status_code == 200
    assert post_greeting_url.headers.get("content-type") == "application/json"
    greeting_response_url = post_greeting_url.json()
    assert (
        greeting_response_url["greeting"]
        == "Hello jsantos thanks for the/third/of/his/name"
    )

    post_greeting = app_client.post("/v1.0/greeting/jsantos", data={})
    assert post_greeting.status_code == 200
    assert post_greeting.headers.get("content-type") == "application/json"
    greeting_response = post_greeting.json()
    assert greeting_response["greeting"] == "Hello jsantos"

    get_bye = app_client.get("/v1.0/bye/jsantos")
    assert get_bye.status_code == 200
    assert get_bye.text == "Goodbye jsantos"

    post_greeting = app_client.post("/v1.0/greeting/jsantos", data={})
    assert post_greeting.status_code == 200
    assert post_greeting.headers.get("content-type") == "application/json"
    greeting_response = post_greeting.json()
    assert greeting_response["greeting"] == "Hello jsantos"


def test_openapi_yaml_behind_proxy(reverse_proxied_app):
    """Verify the swagger.json file is returned with base_path updated
    according to X-Original-URI header.
    """
    app_client = reverse_proxied_app.test_client()

    headers = {"X-Forwarded-Path": "/behind/proxy"}

    swagger_ui = app_client.get("/v1.0/ui/", headers=headers)
    assert swagger_ui.status_code == 200

    openapi_yaml = app_client.get(
        "/v1.0/" + reverse_proxied_app._spec_file, headers=headers
    )
    assert openapi_yaml.status_code == 200
    assert openapi_yaml.headers.get("Content-Type").startswith("text/yaml")
    spec = yaml.load(openapi_yaml.text, Loader=yaml.BaseLoader)

    if reverse_proxied_app._spec_file == "swagger.yaml":
        assert 'url: "/behind/proxy/v1.0/swagger.json"' in swagger_ui.text
        assert (
            spec.get("basePath") == "/behind/proxy/v1.0"
        ), "basePath should contains original URI"
    else:
        assert 'url: "/behind/proxy/v1.0/openapi.json"' in swagger_ui.text
        url = spec.get("servers", [{}])[0].get("url")
        assert url == "/behind/proxy/v1.0", "basePath should contains original URI"


def test_produce_decorator(simple_app):
    app_client = simple_app.test_client()

    get_bye = app_client.get("/v1.0/bye/jsantos")
    assert get_bye.headers.get("content-type", "").startswith("text/plain")


def test_returning_response_tuple(simple_app):
    app_client = simple_app.test_client()

    result = app_client.get("/v1.0/response_tuple")
    assert result.status_code == 201, result.text
    assert result.headers.get("content-type") == "application/json"
    result_data = result.json()
    assert result_data == {"foo": "bar"}


def test_jsonifier(simple_app):
    app_client = simple_app.test_client()

    post_greeting = app_client.post("/v1.0/greeting/jsantos")
    assert post_greeting.status_code == 200
    assert post_greeting.headers.get("content-type") == "application/json"
    greeting_response = post_greeting.json()
    assert greeting_response["greeting"] == "Hello jsantos"

    get_list_greeting = app_client.get("/v1.0/list/jsantos")
    assert get_list_greeting.status_code == 200
    assert get_list_greeting.headers.get("content-type") == "application/json"
    greeting_response = get_list_greeting.json()
    assert len(greeting_response) == 2
    assert greeting_response[0] == "hello"
    assert greeting_response[1] == "jsantos"

    get_greetings = app_client.get("/v1.0/greetings/jsantos")
    assert get_greetings.status_code == 200
    assert get_greetings.headers.get("content-type") == "application/x.connexion+json"
    greetings_response = get_greetings.json()
    assert len(greetings_response) == 1
    assert greetings_response["greetings"] == "Hello jsantos"


def test_not_content_response(simple_app):
    app_client = simple_app.test_client()

    get_no_content_response = app_client.get("/v1.0/test_no_content_response")
    assert get_no_content_response.status_code == 204
    assert get_no_content_response.headers.get("content-length") is None


def test_pass_through(simple_app):
    app_client = simple_app.test_client()

    response = app_client.get("/v1.0/multimime")
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert (
        detail == "Multiple response content types are defined in the "
        "operation spec, but the handler response did not specify "
        "which one to return."
    )


def test_can_use_httpstatus_enum(simple_openapi_app):
    app_client = simple_openapi_app.test_client()

    response = app_client.get("/v1.0/httpstatus")
    assert response.status_code == 201


def test_empty(simple_app):
    app_client = simple_app.test_client()

    response = app_client.get("/v1.0/empty")
    assert response.status_code == 204
    assert not response.text


def test_exploded_deep_object_param_endpoint_openapi_simple(simple_openapi_app):
    app_client = simple_openapi_app.test_client()

    response = app_client.get("/v1.0/exploded-deep-object-param?id[foo]=bar")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"foo": "bar", "foo4": "blubb"}


def test_exploded_deep_object_param_endpoint_openapi_multiple_data_types(
    simple_openapi_app,
):
    app_client = simple_openapi_app.test_client()

    response = app_client.get(
        "/v1.0/exploded-deep-object-param?id[foo]=bar&id[fooint]=2&id[fooboo]=false"
    )
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data == {
        "foo": "bar",
        "fooint": 2,
        "fooboo": False,
        "foo4": "blubb",
    }


def test_exploded_deep_object_param_endpoint_openapi_additional_properties(
    simple_openapi_app,
):
    app_client = simple_openapi_app.test_client()

    response = app_client.get(
        "/v1.0/exploded-deep-object-param-additional-properties?id[foo]=bar&id[fooint]=2"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"foo": "bar", "fooint": "2"}


def test_exploded_deep_object_param_endpoint_openapi_additional_properties_false(
    simple_openapi_app,
):
    app_client = simple_openapi_app.test_client()

    response = app_client.get(
        "/v1.0/exploded-deep-object-param?id[foo]=bar&id[foofoo]=barbar"
    )
    assert response.status_code == 400


def test_exploded_deep_object_param_endpoint_openapi_with_dots(simple_openapi_app):
    app_client = simple_openapi_app.test_client()

    response = app_client.get(
        "/v1.0/exploded-deep-object-param-additional-properties?id[foo]=bar&id[foo.foo]=barbar"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"foo": "bar", "foo.foo": "barbar"}


def test_nested_exploded_deep_object_param_endpoint_openapi(simple_openapi_app):
    app_client = simple_openapi_app.test_client()

    response = app_client.get(
        "/v1.0/nested-exploded-deep-object-param?id[foo][foo2]=bar&id[foofoo]=barbar"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {
        "foo": {"foo2": "bar", "foo3": "blubb"},
        "foofoo": "barbar",
    }


def test_redirect_endpoint(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-redirect-endpoint", follow_redirects=False)
    assert resp.status_code == 302


def test_redirect_response_endpoint(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get(
        "/v1.0/test-redirect-response-endpoint", follow_redirects=False
    )
    assert resp.status_code == 302


def test_default_object_body(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-default-object-body", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 200
    response = resp.json()
    assert response["stack"] == {"image_version": "default_image"}

    resp = app_client.post(
        "/v1.0/test-default-integer-body", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 200
    response = resp.json()
    assert response == 1


def test_required_body(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-required-body", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 400

    resp = app_client.post("/v1.0/test-required-body", json={"foo": "bar"})
    assert resp.status_code == 200


def test_empty_object_body(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-empty-object-body",
        json={},
    )
    assert resp.status_code == 200
    response = resp.json()
    assert response["stack"] == {}


def test_nested_additional_properties(simple_openapi_app):
    app_client = simple_openapi_app.test_client()
    resp = app_client.post(
        "/v1.0/test-nested-additional-properties",
        json={"nested": {"object": True}},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    response = resp.json()
    assert response == {"nested": {"object": True}}


def test_custom_provider(spec):
    simple_flask_app = build_app_from_fixture(
        "simple", app_class=FlaskApp, spec_file=spec, validate_responses=True
    )

    class CustomProvider(FlaskJSONProvider):
        def default(self, o):
            if o.__class__.__name__ == "DummyClass":
                return "cool result"
            return super().default(o)

    flask_app = simple_flask_app.app
    flask_app.json = CustomProvider(flask_app)
    app_client = simple_flask_app.test_client()

    resp = app_client.get("/v1.0/custom-json-response")
    assert resp.status_code == 200
    response = resp.json()
    assert response["theResult"] == "cool result"


def test_content_type_not_json(simple_app):
    app_client = simple_app.test_client()

    resp = app_client.get("/v1.0/blob-response")
    assert resp.status_code == 200

    try:
        # AsyncApp
        content = resp.content
    except AttributeError:
        # FlaskApp
        content = resp.data

    # validate binary content
    text, number = unpack("!4sh", content)
    assert text == b"cool"
    assert number == 8


def test_maybe_blob_or_json(simple_app):
    app_client = simple_app.test_client()

    resp = app_client.get("/v1.0/binary-response")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/octet-stream"

    try:
        # AsyncApp
        content = resp.content
    except AttributeError:
        # FlaskApp
        content = resp.data

    # validate binary content
    text, number = unpack("!4sh", content)
    assert text == b"cool"
    assert number == 8


def test_bad_operations(bad_operations_app):
    # Bad operationIds in bad_operations_app should result in 501
    app_client = bad_operations_app.test_client()

    resp = app_client.get("/v1.0/welcome")
    assert resp.status_code == 501

    resp = app_client.put("/v1.0/welcome")
    assert resp.status_code == 501

    resp = app_client.post("/v1.0/welcome")
    assert resp.status_code == 501


def test_text_request(simple_app):
    app_client = simple_app.test_client()

    resp = app_client.post("/v1.0/text-request", content="text")
    assert resp.status_code == 200


def test_operation_handler_returns_flask_object(invalid_resp_allowed_app):
    app_client = invalid_resp_allowed_app.test_client()
    resp = app_client.get("/v1.0/get_non_conforming_response")
    assert resp.status_code == 200


def test_post_wrong_content_type(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/post_wrong_content_type",
        headers={"content-type": "application/xml"},
        json={"some": "data"},
    )
    assert resp.status_code == 415

    resp = app_client.post(
        "/v1.0/post_wrong_content_type",
        headers={"content-type": "application/x-www-form-urlencoded"},
        content="a=1&b=2",
    )
    assert resp.status_code == 415

    resp = app_client.post(
        "/v1.0/post_wrong_content_type",
        headers={"content-type": "application/json"},
        content="not a valid json",
    )
    assert (
        resp.status_code == 400
    ), "Should return 400 when Content-Type is json but content not parsable"


def test_get_unicode_response(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/get_unicode_response")
    actualJson = {"currency": "\xa3", "key": "leena"}
    assert resp.json() == actualJson


def test_get_enum_response(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/get_enum_response")
    assert resp.status_code == 200


def test_get_httpstatus_response(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/get_httpstatus_response")
    assert resp.status_code == 200


def test_get_bad_default_response(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/get_bad_default_response/200")
    assert resp.status_code == 200

    resp = app_client.get("/v1.0/get_bad_default_response/202")
    assert resp.status_code == 500


def test_streaming_response(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/get_streaming_response")
    assert resp.status_code == 200, resp.text


def test_oneof(simple_openapi_app):
    app_client = simple_openapi_app.test_client()

    post_greeting = app_client.post(
        "/v1.0/oneof_greeting",
        json={"name": 3},
    )
    assert post_greeting.status_code == 200
    assert post_greeting.headers.get("content-type") == "application/json"
    greeting_response = post_greeting.json()
    assert greeting_response["greeting"] == "Hello 3"

    post_greeting = app_client.post(
        "/v1.0/oneof_greeting",
        json={"name": True},
    )
    assert post_greeting.status_code == 200
    assert post_greeting.headers.get("content-type") == "application/json"
    greeting_response = post_greeting.json()
    assert greeting_response["greeting"] == "Hello True"

    post_greeting = app_client.post(
        "/v1.0/oneof_greeting",
        json={"name": "jsantos"},
    )
    assert post_greeting.status_code == 400
