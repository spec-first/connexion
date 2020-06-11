import json

import jinja2
from unittest import mock
import pytest
import yaml
from openapi_spec_validator.loaders import ExtendedSafeLoader

from conftest import TEST_FOLDER, FIXTURES_FOLDER
from sanic.response import text

from connexion import SanicApp as App
from connexion.exceptions import InvalidSpecification
from connexion.http_facts import METHODS

SPECS = ["swagger.yaml", "openapi.yaml"]
OPENAPI3_SPEC = [
    "openapi.yaml",
]


def build_app_from_fixture(api_spec_folder, spec_file="openapi.yaml", **kwargs):
    debug = True
    if "debug" in kwargs:
        debug = kwargs["debug"]
        del kwargs["debug"]

    cnx_app = App(
        __name__,
        port=5001,
        specification_dir=FIXTURES_FOLDER / api_spec_folder,
        debug=debug,
    )

    cnx_app.add_api(spec_file, **kwargs)
    cnx_app._spec_file = spec_file
    return cnx_app


@pytest.fixture(scope="session", params=SPECS)
def simple_app(request):
    return build_app_from_fixture("sanic", request.param, validate_responses=True)


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_relative_path(sanic_api_spec_dir, spec):
    # Create the app with a relative path and run the test_app testcase below.
    app = App(
        __name__,
        port=5001,
        specification_dir="tests" / sanic_api_spec_dir.relative_to(TEST_FOLDER),
        debug=True,
    )
    app.add_api(spec)

    app_client = app.app.test_client
    _, get_bye = app_client.get("/v1.0/bye/jsantos")  # type: httpx.models.Response
    assert get_bye.status_code == 200
    assert get_bye.content == b"Goodbye jsantos"


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_resolver(sanic_api_spec_dir, spec):
    from connexion.resolver import Resolver

    resolver = Resolver()
    app = App(
        __name__,
        port=5001,
        specification_dir=".." / sanic_api_spec_dir.relative_to(TEST_FOLDER),
        resolver=resolver,
    )
    api = app.add_api(spec)
    assert api.resolver is resolver


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_different_server_option(sanic_api_spec_dir, spec):
    # Create the app with a relative path and run the test_app testcase below.
    app = App(
        __name__,
        port=5001,
        server="gevent",
        specification_dir=".." / sanic_api_spec_dir.relative_to(TEST_FOLDER),
        debug=True,
    )
    app.add_api(spec)

    app_client = app.app.test_client
    get_bye = app_client.get("/v1.0/bye/jsantos")  # type: httpx.models.Response
    assert get_bye.status_code == 200
    assert get_bye.content == b"Goodbye jsantos"


def test_app_with_different_uri_parser(sanic_api_spec_dir):
    from connexion.decorators.uri_parsing import FirstValueURIParser

    app = App(
        __name__,
        port=5001,
        specification_dir=".." / sanic_api_spec_dir.relative_to(TEST_FOLDER),
        options={"uri_parser_class": FirstValueURIParser},
        debug=True,
    )
    app.add_api("swagger.yaml")

    app_client = app.app.test_client
    resp = app_client.get(
        "/v1.0/test_array_csv_query_param?items=a,b,c&items=d,e,f"
    )  # type: httpx.models.Response
    assert resp.status_code == 200
    j = json.loads(resp.get_data(as_text=True))
    assert j == ["a", "b", "c"]


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_ui(sanic_api_spec_dir, spec):
    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(spec)
    app_client = app.app.test_client
    _, swagger_ui = app_client.get("/v1.0/ui/")  # type: httpx.models.Response
    assert swagger_ui.status_code == 200
    spec_json_filename = spec_url(spec)
    assert spec_json_filename.encode() in swagger_ui.data
    if "openapi" in spec:
        assert b"swagger-ui-config.json" not in swagger_ui.data


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_ui_with_config(sanic_api_spec_dir, spec):
    swagger_ui_config = {"displayOperationId": True}
    options = {"swagger_ui_config": swagger_ui_config}
    app = App(
        __name__,
        port=5001,
        specification_dir=sanic_api_spec_dir,
        options=options,
        debug=True,
    )
    app.add_api(spec)
    app_client = app.app.test_client
    _, swagger_ui = app_client.get("/v1.0/ui/")  # type: httpx.models.Response
    assert swagger_ui.status_code == 200
    if "openapi" in spec:
        assert b'configUrl: "swagger-ui-config.json"' in swagger_ui.data


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_ui(sanic_api_spec_dir, spec):
    options = {"swagger_ui": False}
    app = App(
        __name__,
        port=5001,
        specification_dir=sanic_api_spec_dir,
        options=options,
        debug=True,
    )
    app.add_api(spec)

    app_client = app.app.test_client
    _, swagger_ui = app_client.get("/v1.0/ui/")  # type: httpx.models.Response
    assert swagger_ui.status_code == 404

    app2 = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app2.add_api(spec, options={"swagger_ui": False})
    app2_client = app2.app.test_client
    _, swagger_ui2 = app2_client.get("/v1.0/ui/")  # type: httpx.models.Response
    assert swagger_ui2.status_code == 404


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_ui_config_json(sanic_api_spec_dir, spec):
    """ Verify the swagger-ui-config.json file is returned for swagger_ui_config option passed to app. """
    swagger_ui_config = {"displayOperationId": True}
    options = {"swagger_ui_config": swagger_ui_config}
    app = App(
        __name__,
        port=5001,
        specification_dir=sanic_api_spec_dir,
        options=options,
        debug=True,
    )
    app.add_api(spec)
    app_client = app.app.test_client
    url = "/v1.0/ui/swagger-ui-config.json"
    _, swagger_ui_config_json = app_client.get(url)  # type: httpx.models.Response
    assert swagger_ui_config_json.status_code == 200
    assert swagger_ui_config == json.loads(
        swagger_ui_config_json.get_data(as_text=True)
    )


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_ui_config_json(sanic_api_spec_dir, spec):
    """ Verify the swagger-ui-config.json file is not returned when the swagger_ui_config option not passed to app. """
    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(spec)
    app_client = app.app.test_client
    url = "/v1.0/ui/swagger-ui-config.json"
    _, swagger_ui_config_json = app_client.get(url)  # type: httpx.models.Response
    assert swagger_ui_config_json.status_code == 404


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_json_app(sanic_api_spec_dir, spec):
    """ Verify the spec json file is returned for default setting passed to app. """
    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(spec)
    app_client = app.app.test_client
    url = spec_url(spec)
    _, spec_json = app_client.get(url)  # type: httpx.models.Response
    assert spec_json.status_code == 200


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_yaml_app(sanic_api_spec_dir, spec):
    """ Verify the spec yaml file is returned for default setting passed to app. """
    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(spec)
    app_client = app.app.test_client
    url = "/v1.0/{spec}"
    url = url.format(spec=spec)
    _, spec_response = app_client.get(url)  # type: httpx.models.Response
    assert spec_response.status_code == 200


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_json_app(sanic_api_spec_dir, spec):
    """ Verify the spec json file is not returned when set to False when creating app. """
    options = {"serve_spec": False}
    app = App(
        __name__,
        port=5001,
        specification_dir=sanic_api_spec_dir,
        options=options,
        debug=True,
    )
    app.add_api(spec)

    app_client = app.app.test_client
    url = spec_url(spec)
    _, spec_json = app_client.get(url)  # type: httpx.models.Response
    assert spec_json.status_code == 404


@pytest.mark.parametrize("spec", SPECS)
def test_dict_as_yaml_path(sanic_api_spec_dir, spec):
    openapi_yaml_path = sanic_api_spec_dir / spec

    with openapi_yaml_path.open(mode="rb") as openapi_yaml:
        contents = openapi_yaml.read()
        try:
            openapi_template = contents.decode()
        except UnicodeDecodeError:
            openapi_template = contents.decode("utf-8", "replace")

        openapi_string = jinja2.Template(openapi_template).render({})
        specification = yaml.load(openapi_string, ExtendedSafeLoader)  # type: dict

    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(specification)

    app_client = app.app.test_client
    url = spec_url(spec)
    _, swagger_json = app_client.get(url)  # type: httpx.models.Response
    assert swagger_json.status_code == 200


def spec_url(spec):
    spec = "openapi" if "openapi" in spec else "swagger"
    return "/v1.0/{spec}.json".format(spec=spec)


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_json_api(sanic_api_spec_dir, spec):
    """ Verify the spec json file is returned for default setting passed to api. """
    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(spec)

    app_client = app.app.test_client
    url = spec_url(spec)
    _, swagger_json = app_client.get(url)  # type: httpx.models.Response
    assert swagger_json.status_code == 200


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_json_api(sanic_api_spec_dir, spec):
    """ Verify the spec json file is not returned when set to False when adding api. """
    app = App(__name__, port=5001, specification_dir=sanic_api_spec_dir, debug=True)
    app.add_api(spec, options={"serve_spec": False})

    app_client = app.app.test_client
    url = spec_url(spec)
    _, swagger_json = app_client.get(url)  # type: httpx.models.Response
    assert swagger_json.status_code == 404


def test_swagger_json_content_type(simple_app):
    app_client = simple_app.app.test_client
    spec = simple_app._spec_file
    url = spec_url(spec)
    _, response = app_client.get(url)  # type: httpx.models.Response
    assert response.status_code == 200
    assert response.content_type == "application/json"


def test_single_route(simple_app):
    async def route1(request):
        return text("single 1")

    @simple_app.app.route("/single2", methods=["POST"])
    def route2(request):
        return text("single 2")

    app_client = simple_app.app.test_client

    simple_app.app.add_route(
        uri="/single1", name="single1", handler=route1, methods=["GET"]
    )

    _, get_single1 = app_client.get("/single1")  # type: httpx.models.Response
    assert get_single1.content == b"single 1"

    _, post_single1 = app_client.post("/single1")  # type: httpx.models.Response
    assert post_single1.status_code == 405

    _, post_single2 = app_client.post("/single2")  # type: httpx.models.Response
    assert post_single2.content == b"single 2"

    _, get_single2 = app_client.get("/single2")  # type: httpx.models.Response
    assert get_single2.status_code == 405


def test_resolve_method(simple_app):
    app_client = simple_app.app.test_client
    _, resp = app_client.get(
        "/v1.0/resolver-test/method"
    )  # type: httpx.models.Response
    assert resp.content == b'"DummyClass"\n'


def test_resolve_classmethod(simple_app):
    app_client = simple_app.app.test_client
    _, resp = app_client.get(
        "/v1.0/resolver-test/classmethod"
    )  # type: httpx.models.Response
    assert resp.content.decode("utf-8", "replace") == '"DummyClass"\n'


@pytest.mark.parametrize("spec", SPECS)
def test_add_api_with_function_resolver_function_is_wrapped(sanic_api_spec_dir, spec):
    app = App(__name__, specification_dir=sanic_api_spec_dir)
    api = app.add_api(spec, resolver=lambda oid: (lambda foo: "bar"))
    assert api.resolver.resolve_function_from_operation_id("faux")("bah") == "bar"


def test_default_query_param_does_not_match_defined_type(default_param_error_spec_dir):
    with pytest.raises(InvalidSpecification):
        build_app_from_fixture(
            default_param_error_spec_dir, validate_responses=True, debug=False
        )


def test_handle_add_operation_error_debug(sanic_api_spec_dir):
    app = App(__name__, specification_dir=sanic_api_spec_dir, debug=True)
    app.api_cls = type("AppTest", (app.api_cls,), {})
    app.api_cls.add_operation = mock.MagicMock(
        side_effect=Exception("operation error!")
    )
    api = app.add_api("swagger.yaml", resolver=lambda oid: (lambda foo: "bar"))
    assert app.api_cls.add_operation.called
    assert api.resolver.resolve_function_from_operation_id("faux")("bah") == "bar"


def test_handle_add_operation_error(sanic_api_spec_dir):
    app = App(__name__, specification_dir=sanic_api_spec_dir)
    app.api_cls = type("AppTest", (app.api_cls,), {})
    app.api_cls.add_operation = mock.MagicMock(
        side_effect=Exception("operation error!")
    )
    with pytest.raises(Exception):
        app.add_api("swagger.yaml", resolver=lambda oid: (lambda foo: "bar"))


def test_using_all_fields_in_path_item(sanic_api_spec_dir):
    """Test that connexion will try to add an endpoint only on http methods.

    test also that each http methods has its own endpoint.
    """
    app = App(__name__, specification_dir=sanic_api_spec_dir)
    app.add_api("openapi.yaml")

    test_methods = set()
    for rule in app.app.url_map.iter_rules():
        if rule.rule != "/v1.0/add_operation_on_http_methods_only":
            continue
        test_methods.update({method.lower() for method in rule.methods})
    assert set(test_methods) == METHODS
