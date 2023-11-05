import json
from unittest import mock

import jinja2
import pytest
import yaml
from connexion import App
from connexion.exceptions import InvalidSpecification
from connexion.http_facts import METHODS
from connexion.json_schema import ExtendedSafeLoader
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware.abstract import AbstractRoutingAPI
from connexion.options import SwaggerUIOptions

from conftest import TEST_FOLDER, build_app_from_fixture


def test_app_with_relative_path(simple_api_spec_dir, spec):
    # Create the app with a relative path and run the test_app testcase below.
    app = App(
        __name__,
        specification_dir=".." / simple_api_spec_dir.relative_to(TEST_FOLDER),
    )
    app.add_api(spec)

    app_client = app.test_client()
    get_bye = app_client.get("/v1.0/bye/jsantos")
    assert get_bye.status_code == 200
    assert get_bye.text == "Goodbye jsantos"


def test_app_with_different_uri_parser(simple_api_spec_dir):
    from connexion.uri_parsing import FirstValueURIParser

    app = App(
        __name__,
        specification_dir=".." / simple_api_spec_dir.relative_to(TEST_FOLDER),
        uri_parser_class=FirstValueURIParser,
    )
    app.add_api("swagger.yaml")

    app_client = app.test_client()
    resp = app_client.get("/v1.0/test_array_csv_query_param?items=a,b,c&items=d,e,f")
    assert resp.status_code == 200
    j = resp.json()
    assert j == ["a", "b", "c"]


def test_swagger_ui(simple_api_spec_dir, spec):
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(spec)
    app_client = app.test_client()
    swagger_ui = app_client.get("/v1.0/ui/")
    assert swagger_ui.status_code == 200
    spec_json_filename = "/v1.0/{spec}".format(spec=spec.replace("yaml", "json"))
    assert spec_json_filename in swagger_ui.text
    if "openapi" in spec:
        assert "swagger-ui-config.json" not in swagger_ui.text


def test_swagger_ui_with_config(simple_api_spec_dir, spec):
    swagger_ui_config = {"displayOperationId": True}
    swagger_ui_options = SwaggerUIOptions(swagger_ui_config=swagger_ui_config)
    app = App(
        __name__,
        specification_dir=simple_api_spec_dir,
        swagger_ui_options=swagger_ui_options,
    )
    app.add_api(spec)
    app_client = app.test_client()
    swagger_ui = app_client.get("/v1.0/ui/")
    assert swagger_ui.status_code == 200
    if "openapi" in spec:
        assert 'configUrl: "swagger-ui-config.json"' in swagger_ui.text


def test_no_swagger_ui(simple_api_spec_dir, spec):
    swagger_ui_options = SwaggerUIOptions(swagger_ui=False)
    app = App(
        __name__,
        specification_dir=simple_api_spec_dir,
        swagger_ui_options=swagger_ui_options,
    )
    app.add_api(spec)

    app_client = app.test_client()
    swagger_ui = app_client.get("/v1.0/ui/")
    assert swagger_ui.status_code == 404

    app2 = App(__name__, specification_dir=simple_api_spec_dir)
    app2.add_api(spec, swagger_ui_options=SwaggerUIOptions(swagger_ui=False))
    app2_client = app2.test_client()
    swagger_ui2 = app2_client.get("/v1.0/ui/")
    assert swagger_ui2.status_code == 404


def test_swagger_ui_config_json(simple_api_spec_dir, spec):
    """Verify the swagger-ui-config.json file is returned for swagger_ui_config option passed to app."""
    swagger_ui_config = {"displayOperationId": True}
    swagger_ui_options = SwaggerUIOptions(swagger_ui_config=swagger_ui_config)
    app = App(
        __name__,
        specification_dir=simple_api_spec_dir,
        swagger_ui_options=swagger_ui_options,
    )
    app.add_api(spec)
    app_client = app.test_client()
    url = "/v1.0/ui/swagger-ui-config.json"
    swagger_ui_config_json = app_client.get(url)
    assert swagger_ui_config_json.status_code == 200
    assert swagger_ui_config == swagger_ui_config_json.json()


def test_no_swagger_ui_config_json(simple_api_spec_dir, spec):
    """Verify the swagger-ui-config.json file is not returned when the swagger_ui_config option not passed to app."""
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(spec)
    app_client = app.test_client()
    url = "/v1.0/ui/swagger-ui-config.json"
    swagger_ui_config_json = app_client.get(url)
    assert swagger_ui_config_json.status_code == 404


def test_swagger_json_app(simple_api_spec_dir, spec):
    """Verify the spec json file is returned for default setting passed to app."""
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(spec)
    app_client = app.test_client()
    url = "/v1.0/{spec}"
    url = url.format(spec=spec.replace("yaml", "json"))
    spec_json = app_client.get(url)
    assert spec_json.status_code == 200


def test_swagger_yaml_app(simple_api_spec_dir, spec):
    """Verify the spec yaml file is returned for default setting passed to app."""
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(spec)
    app_client = app.test_client()
    url = "/v1.0/{spec}"
    url = url.format(spec=spec)
    spec_response = app_client.get(url)
    assert spec_response.status_code == 200


def test_no_swagger_json_app(simple_api_spec_dir, spec):
    """Verify the spec json file is not returned when set to False when creating app."""
    swagger_ui_options = SwaggerUIOptions(serve_spec=False)
    app = App(
        __name__,
        specification_dir=simple_api_spec_dir,
        swagger_ui_options=swagger_ui_options,
    )
    app.add_api(spec)

    app_client = app.test_client()
    url = "/v1.0/{spec}"
    url = url.format(spec=spec.replace("yaml", "json"))
    spec_json = app_client.get(url)
    assert spec_json.status_code == 404


def test_dict_as_yaml_path(simple_api_spec_dir, spec):
    openapi_yaml_path = simple_api_spec_dir / spec

    with openapi_yaml_path.open(mode="rb") as openapi_yaml:
        contents = openapi_yaml.read()
        try:
            openapi_template = contents.decode()
        except UnicodeDecodeError:
            openapi_template = contents.decode("utf-8", "replace")

        openapi_string = jinja2.Template(openapi_template).render({})
        specification = yaml.load(openapi_string, ExtendedSafeLoader)  # type: dict

    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(specification)

    app_client = app.test_client()
    url = "/v1.0/{spec}".format(spec=spec.replace("yaml", "json"))
    swagger_json = app_client.get(url)
    assert swagger_json.status_code == 200


def test_swagger_json_api(simple_api_spec_dir, spec):
    """Verify the spec json file is returned for default setting passed to api."""
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(spec)

    app_client = app.test_client()
    url = "/v1.0/{spec}".format(spec=spec.replace("yaml", "json"))
    swagger_json = app_client.get(url)
    assert swagger_json.status_code == 200


def test_no_swagger_json_api(simple_api_spec_dir, spec):
    """Verify the spec json file is not returned when set to False when adding api."""
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api(spec, swagger_ui_options=SwaggerUIOptions(serve_spec=False))

    app_client = app.test_client()
    url = "/v1.0/{spec}".format(spec=spec.replace("yaml", "json"))
    swagger_json = app_client.get(url)
    assert swagger_json.status_code == 404


def test_swagger_json_content_type(simple_app):
    app_client = simple_app.test_client()
    spec = simple_app._spec_file
    url = "/v1.0/{spec}".format(spec=spec.replace("yaml", "json"))
    response = app_client.get(url)
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json"


def test_single_route():
    app = App(__name__)

    def route1():
        return "single 1"

    @app.route("/single2", methods=["POST"])
    def route2():
        return "single 2"

    app_client = app.test_client()

    app.add_url_rule("/single1", "single1", route1, methods=["GET"])

    get_single1 = app_client.get("/single1")
    assert get_single1.text == "single 1"

    post_single1 = app_client.post("/single1")
    assert post_single1.status_code == 405

    post_single2 = app_client.post("/single2")
    assert post_single2.text == "single 2"

    get_single2 = app_client.get("/single2")
    assert get_single2.status_code == 405


def test_resolve_method(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/resolver-test/method")
    assert resp.text == '"DummyClass"\n'


def test_resolve_classmethod(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/resolver-test/classmethod")
    assert resp.text == '"DummyClass"\n'


def test_default_query_param_does_not_match_defined_type(
    default_param_error_spec_dir, app_class, spec
):
    with pytest.raises(InvalidSpecification):
        app = build_app_from_fixture(
            default_param_error_spec_dir,
            app_class=app_class,
            spec_file=spec,
            validate_responses=True,
        )
        app.middleware._build_middleware_stack()


def test_handle_add_operation_error(simple_api_spec_dir, monkeypatch):
    app = App(__name__, specification_dir=simple_api_spec_dir)
    monkeypatch.setattr(
        AbstractRoutingAPI,
        "add_operation",
        mock.MagicMock(side_effect=Exception("operation error!")),
    )
    with pytest.raises(Exception):
        app.add_api("swagger.yaml", resolver=lambda oid: (lambda foo: "bar"))
        app.middleware._build_middleware_stack()


def test_using_all_fields_in_path_item(simple_api_spec_dir):
    """Test that connexion will try to add an endpoint only on http methods.

    test also that each http methods has its own endpoint.
    """
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.add_api("openapi.yaml")
    app.middleware._build_middleware_stack()

    test_methods = set()
    for rule in app.app.url_map.iter_rules():
        if rule.rule != "/v1.0/add_operation_on_http_methods_only":
            continue
        test_methods.update({method.lower() for method in rule.methods})
    assert set(test_methods) == METHODS


def test_async_route(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/async-route")
    assert resp.status_code == 200


def test_add_error_handler(app_class, simple_api_spec_dir):
    app = app_class(__name__, specification_dir=simple_api_spec_dir)
    app.add_api("openapi.yaml")

    def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
        return ConnexionResponse(
            status_code=404, body=json.dumps({"error": "NotFound"})
        )

    app.add_error_handler(404, not_found)

    app_client = app.test_client()

    response = app_client.get("/does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"
