import yaml

import jinja2
import pytest
from conftest import TEST_FOLDER, build_app_from_fixture
from connexion import FlaskApp
from connexion.exceptions import InvalidSpecification


def test_app_with_relative_path(simple_api_spec_dir):
    # Create the app with a realative path and run the test_app testcase below.
    app = FlaskApp(__name__, 5001, '..' / simple_api_spec_dir.relative_to(TEST_FOLDER),
              debug=True)
    app.add_api('swagger.yaml')

    app_client = app.app.test_client()
    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'


def test_no_swagger_ui(simple_api_spec_dir):
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, swagger_ui=False, debug=True)
    app.add_api('swagger.yaml')

    app_client = app.app.test_client()
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 404

    app2 = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app2.add_api('swagger.yaml', swagger_ui=False)
    app2_client = app2.app.test_client()
    swagger_ui2 = app2_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui2.status_code == 404


def test_swagger_json_app(simple_api_spec_dir):
    """ Verify the swagger.json file is returned for default setting passed to app. """
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app.add_api('swagger.yaml')

    app_client = app.app.test_client()
    swagger_json = app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status_code == 200


def test_no_swagger_json_app(simple_api_spec_dir):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, swagger_json=False, debug=True)
    app.add_api('swagger.yaml')

    app_client = app.app.test_client()
    swagger_json = app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status_code == 404


def test_dict_as_yaml_path(simple_api_spec_dir):

    swagger_yaml_path = simple_api_spec_dir / 'swagger.yaml'

    with swagger_yaml_path.open(mode='rb') as swagger_yaml:
        contents = swagger_yaml.read()
        try:
            swagger_template = contents.decode()
        except UnicodeDecodeError:
            swagger_template = contents.decode('utf-8', 'replace')

        swagger_string = jinja2.Template(swagger_template).render({})
        specification = yaml.safe_load(swagger_string)  # type: dict

    app = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app.add_api(specification)

    app_client = app.app.test_client()
    swagger_json = app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status_code == 200


def test_swagger_json_api(simple_api_spec_dir):
    """ Verify the swagger.json file is returned for default setting passed to api. """
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app.add_api('swagger.yaml')

    app_client = app.app.test_client()
    swagger_json = app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status_code == 200


def test_no_swagger_json_api(simple_api_spec_dir):
    """ Verify the swagger.json file is not returned when set to False when adding api. """
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app.add_api('swagger.yaml', swagger_json=False)

    app_client = app.app.test_client()
    swagger_json = app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status_code == 404


def test_swagger_json_content_type(simple_app):
    app_client = simple_app.app.test_client()

    response = app_client.get('/v1.0/swagger.json',
                              data={})  # type: flask.Response
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


def test_add_api_with_function_resolver_function_is_wrapped(simple_api_spec_dir):
    app = FlaskApp(__name__, specification_dir=simple_api_spec_dir)
    api = app.add_api('swagger.yaml', resolver=lambda oid: (lambda foo: 'bar'))
    assert api.resolver.resolve_function_from_operation_id('faux')('bah') == 'bar'


def test_default_query_param_does_not_match_defined_type(
        default_param_error_spec_dir):
    with pytest.raises(InvalidSpecification):
        build_app_from_fixture(default_param_error_spec_dir, validate_responses=True, debug=False)
