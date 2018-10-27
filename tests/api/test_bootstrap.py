import json

import jinja2
import yaml
from openapi_spec_validator.loaders import ExtendedSafeLoader

import mock
import pytest
from conftest import TEST_FOLDER, build_app_from_fixture
from connexion import App
from connexion.exceptions import InvalidSpecification

SPECS = ["swagger.yaml", "openapi.yaml"]


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_relative_path(simple_api_spec_dir, spec):
    # Create the app with a relative path and run the test_app testcase below.
    app = App(__name__, port=5001,
              specification_dir='..' / simple_api_spec_dir.relative_to(TEST_FOLDER),
              debug=True)
    app.add_api(spec)

    app_client = app.app.test_client()
    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_resolver(simple_api_spec_dir, spec):
    from connexion.resolver import Resolver
    resolver = Resolver()
    app = App(__name__, port=5001,
              specification_dir='..' / simple_api_spec_dir.relative_to(TEST_FOLDER),
              resolver=resolver)
    api = app.add_api(spec)
    assert api.resolver is resolver


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_different_server_option(simple_api_spec_dir, spec):
    # Create the app with a relative path and run the test_app testcase below.
    app = App(__name__, port=5001,
              server='gevent',
              specification_dir='..' / simple_api_spec_dir.relative_to(TEST_FOLDER),
              debug=True)
    app.add_api(spec)

    app_client = app.app.test_client()
    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'


def test_app_with_different_uri_parser(simple_api_spec_dir):
    from connexion.decorators.uri_parsing import FirstValueURIParser
    app = App(__name__, port=5001,
              specification_dir='..' / simple_api_spec_dir.relative_to(TEST_FOLDER),
              options={"uri_parser_class": FirstValueURIParser},
              debug=True)
    app.add_api('swagger.yaml')

    app_client = app.app.test_client()
    resp = app_client.get(
        '/v1.0/test_array_csv_query_param?items=a,b,c&items=d,e,f'
    )  # type: flask.Response
    assert resp.status_code == 200
    j = json.loads(resp.get_data(as_text=True))
    assert j == ['a', 'b', 'c']


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_ui(simple_api_spec_dir, spec):
    options = {"swagger_ui": False}
    app = App(__name__, port=5001, specification_dir=simple_api_spec_dir,
              options=options, debug=True)
    app.add_api(spec)

    app_client = app.app.test_client()
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 404

    app2 = App(__name__, port=5001, specification_dir=simple_api_spec_dir, debug=True)
    app2.add_api(spec, options={"swagger_ui": False})
    app2_client = app2.app.test_client()
    swagger_ui2 = app2_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui2.status_code == 404


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_json_app(simple_api_spec_dir, spec):
    """ Verify the spec json file is returned for default setting passed to app. """
    app = App(__name__, port=5001, specification_dir=simple_api_spec_dir, debug=True)
    app.add_api(spec)
    app_client = app.app.test_client()
    url = '/v1.0/{spec}'
    url = url.format(spec=spec.replace("yaml", "json"))
    spec_json = app_client.get(url)  # type: flask.Response
    assert spec_json.status_code == 200


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_json_app(simple_api_spec_dir, spec):
    """ Verify the spec json file is not returned when set to False when creating app. """
    options = {"serve_spec": False}
    app = App(__name__, port=5001, specification_dir=simple_api_spec_dir,
              options=options, debug=True)
    app.add_api(spec)

    app_client = app.app.test_client()
    url = '/v1.0/{spec}'
    url = url.format(spec=spec.replace("yaml", "json"))
    spec_json = app_client.get(url)  # type: flask.Response
    assert spec_json.status_code == 404


@pytest.mark.parametrize("spec", SPECS)
def test_dict_as_yaml_path(simple_api_spec_dir, spec):
    openapi_yaml_path = simple_api_spec_dir / spec

    with openapi_yaml_path.open(mode='rb') as openapi_yaml:
        contents = openapi_yaml.read()
        try:
            openapi_template = contents.decode()
        except UnicodeDecodeError:
            openapi_template = contents.decode('utf-8', 'replace')

        openapi_string = jinja2.Template(openapi_template).render({})
        specification = yaml.load(openapi_string, ExtendedSafeLoader)  # type: dict

    app = App(__name__, port=5001, specification_dir=simple_api_spec_dir, debug=True)
    app.add_api(specification)

    app_client = app.app.test_client()
    url = '/v1.0/{spec}'.format(spec=spec.replace("yaml", "json"))
    swagger_json = app_client.get(url)  # type: flask.Response
    assert swagger_json.status_code == 200


@pytest.mark.parametrize("spec", SPECS)
def test_swagger_json_api(simple_api_spec_dir, spec):
    """ Verify the spec json file is returned for default setting passed to api. """
    app = App(__name__, port=5001, specification_dir=simple_api_spec_dir, debug=True)
    app.add_api(spec)

    app_client = app.app.test_client()
    url = '/v1.0/{spec}'.format(spec=spec.replace("yaml", "json"))
    swagger_json = app_client.get(url)  # type: flask.Response
    assert swagger_json.status_code == 200


@pytest.mark.parametrize("spec", SPECS)
def test_no_swagger_json_api(simple_api_spec_dir, spec):
    """ Verify the spec json file is not returned when set to False when adding api. """
    app = App(__name__, port=5001, specification_dir=simple_api_spec_dir, debug=True)
    app.add_api(spec, options={"serve_spec": False})

    app_client = app.app.test_client()
    url = '/v1.0/{spec}'.format(spec=spec.replace("yaml", "json"))
    swagger_json = app_client.get(url)  # type: flask.Response
    assert swagger_json.status_code == 404


def test_swagger_json_content_type(simple_app):
    app_client = simple_app.app.test_client()
    spec = simple_app._spec_file
    url = '/v1.0/{spec}'.format(spec=spec.replace("yaml", "json"))
    response = app_client.get(url)  # type: flask.Response
    assert response.status_code == 200
    assert response.content_type == 'application/json'


def test_single_route(simple_app):
    def route1():
        return 'single 1'

    @simple_app.route('/single2', methods=['POST'])
    def route2():
        return 'single 2'

    app_client = simple_app.app.test_client()

    simple_app.add_url_rule('/single1', 'single1', route1, methods=['GET'])

    get_single1 = app_client.get('/single1')  # type: flask.Response
    assert get_single1.data == b'single 1'

    post_single1 = app_client.post('/single1')  # type: flask.Response
    assert post_single1.status_code == 405

    post_single2 = app_client.post('/single2')  # type: flask.Response
    assert post_single2.data == b'single 2'

    get_single2 = app_client.get('/single2')  # type: flask.Response
    assert get_single2.status_code == 405


def test_resolve_method(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/resolver-test/method')  # type: flask.Response
    assert resp.data == b'"DummyClass"\n'


def test_resolve_classmethod(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/resolver-test/classmethod')  # type: flask.Response
    assert resp.data.decode('utf-8', 'replace') == '"DummyClass"\n'


@pytest.mark.parametrize("spec", SPECS)
def test_add_api_with_function_resolver_function_is_wrapped(simple_api_spec_dir, spec):
    app = App(__name__, specification_dir=simple_api_spec_dir)
    api = app.add_api(spec, resolver=lambda oid: (lambda foo: 'bar'))
    assert api.resolver.resolve_function_from_operation_id('faux')('bah') == 'bar'


def test_default_query_param_does_not_match_defined_type(
        default_param_error_spec_dir):
    with pytest.raises(InvalidSpecification):
        build_app_from_fixture(default_param_error_spec_dir, validate_responses=True, debug=False)


def test_handle_add_operation_error_debug(simple_api_spec_dir):
    app = App(__name__, specification_dir=simple_api_spec_dir, debug=True)
    app.api_cls = type('AppTest', (app.api_cls,), {})
    app.api_cls.add_operation = mock.MagicMock(side_effect=Exception('operation error!'))
    api = app.add_api('swagger.yaml', resolver=lambda oid: (lambda foo: 'bar'))
    assert app.api_cls.add_operation.called
    assert api.resolver.resolve_function_from_operation_id('faux')('bah') == 'bar'


def test_handle_add_operation_error(simple_api_spec_dir):
    app = App(__name__, specification_dir=simple_api_spec_dir)
    app.api_cls = type('AppTest', (app.api_cls,), {})
    app.api_cls.add_operation = mock.MagicMock(side_effect=Exception('operation error!'))
    with pytest.raises(Exception):
        app.add_api('swagger.yaml', resolver=lambda oid: (lambda foo: 'bar'))
