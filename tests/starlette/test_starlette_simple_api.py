import sys

import pytest
import yaml
from connexion import StarletteApp
from starlette.testclient import TestClient
from urllib.parse import urlparse
from conftest import TEST_FOLDER

try:
    import ujson as json
except ImportError:
    import json


@pytest.fixture
def starlette_app(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    options = {"validate_responses": True}
    app.add_api('swagger_simple.yaml', validate_responses=True, pass_context_arg_name='request_ctx', options=options)
    return app


def test_app(starlette_app):
    # Create the app and run the test_app testcase below.
    app_client = TestClient(starlette_app)
    get_bye = app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status_code == 200
    assert get_bye.content == b'Goodbye jsantos'


def test_app_with_relative_path(starlette_api_spec_dir):
    # Create the app with a relative path and run the test_app testcase below.
    app = StarletteApp(__name__, port=5001,
                     specification_dir='..' /
                                       starlette_api_spec_dir.relative_to(TEST_FOLDER),
                     debug=True)
    app.add_api('swagger_simple.yaml')
    app_client = TestClient(app.app)
    get_bye = app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status_code == 200
    assert get_bye.content == b'Goodbye jsantos'


def test_swagger_json(starlette_api_spec_dir):
    """ Verify the swagger.json file is returned for default setting passed to app. """
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_json = app_client.get('/v1.0/swagger.json')

    assert swagger_json.status_code == 200
    json_ = swagger_json.json()
    assert api.specification.raw == json_


def test_swagger_yaml(starlette_api_spec_dir):
    """ Verify the swagger.yaml file is returned for default setting passed to app. """
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    spec_response = app_client.get('/v1.0/swagger.yaml')
    data_ = spec_response.content

    assert spec_response.status_code == 200
    assert api.specification.raw == yaml.load(data_)


def test_no_swagger_json(starlette_api_spec_dir):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    options = {"swagger_json": False}
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     options=options,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_json = app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status_code == 404


def test_no_swagger_yaml(starlette_api_spec_dir):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    options = {"swagger_json": False}
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     options=options,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    spec_response = app_client.get('/v1.0/swagger.yaml')  # type: flask.Response
    assert spec_response.status_code == 404


def test_swagger_ui(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_ui = app_client.get('/v1.0/ui')
    assert swagger_ui.status_code == 200
    assert urlparse(swagger_ui.url).path == '/v1.0/ui/'
    assert b'url = "/v1.0/swagger.json"' in swagger_ui.content

    swagger_ui = app_client.get('/v1.0/ui/')
    assert swagger_ui.status_code == 200
    assert b'url = "/v1.0/swagger.json"' in swagger_ui.content


def test_swagger_ui_config_json(starlette_api_spec_dir):
    """ Verify the swagger-ui-config.json file is returned for swagger_ui_config option passed to app. """
    swagger_ui_config = {"displayOperationId": True}
    options = {"swagger_ui_config": swagger_ui_config}
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     options=options,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_ui_config_json = app_client.get('/v1.0/ui/swagger-ui-config.json')
    json_ = swagger_ui_config_json.content

    assert swagger_ui_config_json.status_code == 200
    assert swagger_ui_config == json.loads(json_)


def test_no_swagger_ui_config_json(starlette_api_spec_dir):
    """ Verify the swagger-ui-config.json file is not returned when the swagger_ui_config option not passed to app. """
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_ui_config_json = app_client.get('/v1.0/ui/swagger-ui-config.json')
    assert swagger_ui_config_json.status_code == 404


def test_swagger_ui_index(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.add_api('openapi_secure.yaml')

    app_client = TestClient(app.app)
    swagger_ui = app_client.get('/v1.0/ui/index.html')
    assert swagger_ui.status_code == 200
    assert b'url: "/v1.0/openapi.json"' in swagger_ui.content
    assert b'swagger-ui-config.json' not in swagger_ui.content


def test_swagger_ui_index_with_config(starlette_api_spec_dir):
    swagger_ui_config = {"displayOperationId": True}
    options = {"swagger_ui_config": swagger_ui_config}
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     options=options,
                     debug=True)
    app.add_api('openapi_secure.yaml')

    app_client = TestClient(app.app)
    swagger_ui = app_client.get('/v1.0/ui/index.html')
    assert swagger_ui.status_code == 200
    assert b'configUrl: "swagger-ui-config.json"' in swagger_ui.content


def test_pythonic_path_param(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.add_api('openapi_simple.yaml', pythonic_params=True)

    app_client = TestClient(app.app)
    pythonic = app_client.get('/v1.0/pythonic/100')
    assert pythonic.status_code == 200
    j = pythonic.json()
    assert j['id_'] == 100


def test_swagger_ui_static(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_ui = app_client.get('/v1.0/ui/lib/swagger-oauth.js')
    assert swagger_ui.status_code == 200

    app_client = TestClient(app.app)
    swagger_ui = app_client.get('/v1.0/ui/swagger-ui.min.js')
    assert swagger_ui.status_code == 200


def test_no_swagger_ui(starlette_api_spec_dir):
    options = {"swagger_ui": False}
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     options=options, debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = TestClient(app.app)
    swagger_ui = app_client.get('/v1.0/ui/')
    assert swagger_ui.status_code == 404

    app2 = StarletteApp(__name__, port=5001,
                      specification_dir=starlette_api_spec_dir,
                      debug=True)
    options = {"swagger_ui": False}
    app2.add_api('swagger_simple.yaml', options=options)
    app2_client = TestClient(app.app)
    swagger_ui2 = app2_client.get('/v1.0/ui/')
    assert swagger_ui2.status_code == 404


def test_middlewares(starlette_api_spec_dir):
    def middleware(app, handler):
        async def middleware_handler(request):
            response = (await handler(request))
            response.body += b' middleware'
            return response

        return middleware_handler

    options = {"middlewares": [middleware]}
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True, options=options)
    app.add_api('swagger_simple.yaml')
    app_client = TestClient(app.app)
    get_bye = app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status_code == 200
    assert get_bye.content == b'Goodbye jsantos middleware'


def test_response_with_str_body(starlette_app):
    # Create the app and run the test_app testcase below.
    app_client = TestClient(starlette_app.app)
    get_bye = app_client.get('/v1.0/starlette_str_response')
    assert get_bye.status_code == 200
    assert get_bye.content == b'str response'


def test_response_with_non_str_and_non_json_body(starlette_app):
    app_client = TestClient(starlette_app.app)
    get_bye = app_client.get(
        '/v1.0/starlette_non_str_non_json_response'
    )
    assert get_bye.status_code == 200
    assert get_bye.content == b'1234'


def test_response_with_bytes_body(starlette_app):
    # Create the app and run the test_app testcase below.
    app_client = TestClient(starlette_app.app)
    get_bye = app_client.get('/v1.0/starlette_bytes_response')
    assert get_bye.status_code == 200
    assert get_bye.content == b'bytes response'


def test_validate_responses(starlette_app):
    app_client = TestClient(starlette_app.app)
    get_bye = app_client.get('/v1.0/starlette_validate_responses')
    assert get_bye.status_code == 200
    assert get_bye.json() == {"validate": True}


def test_get_users(starlette_app):
    app_client = TestClient(starlette_app.app)
    resp = app_client.get('/v1.0/users')
    assert urlparse(resp.url).path == '/v1.0/users/'  # followed redirect
    assert resp.status_code == 200

    json_data = resp.json()
    assert json_data == \
           [{'name': 'John Doe', 'id': 1}, {'name': 'Nick Carlson', 'id': 2}]


def test_create_user(starlette_app):
    app_client = TestClient(starlette_app.app)
    user = {'name': 'Maksim'}
    resp = app_client.post('/v1.0/users', json=user, headers={'Content-type': 'application/json'})
    assert resp.status_code == 201


def test_access_request_context(starlette_app):
    app_client = TestClient(starlette_app.app)
    resp = app_client.post('/v1.0/starlette_access_request_context/')
    assert resp.status_code == 204


def test_query_parsing_simple(starlette_app):
    expected_query = 'query'

    app_client = TestClient(starlette_app.app)
    resp = app_client.get(
        '/v1.0/starlette_query_parsing_str',
        params={
            'query': expected_query,
        },
    )
    assert resp.status_code == 200

    json_data = resp.json()
    assert json_data == {'query': expected_query}


def test_query_parsing_array(starlette_app):
    expected_query = ['queryA', 'queryB']

    app_client = TestClient(starlette_app.app)
    resp = app_client.get(
        '/v1.0/starlette_query_parsing_array',
        params={
            'query': ','.join(expected_query),
        },
    )
    assert resp.status_code == 200

    json_data = resp.json()
    assert json_data == {'query': expected_query}


def test_query_parsing_array_multi(starlette_app):
    expected_query = ['queryA', 'queryB', 'queryC']
    query_str = '&'.join(['query=%s' % q for q in expected_query])

    app_client = TestClient(starlette_app.app)
    resp = app_client.get(
        '/v1.0/starlette_query_parsing_array_multi?%s' % query_str,
    )
    assert resp.status_code == 200

    json_data = resp.json()
    assert json_data == {'query': expected_query}


if sys.version_info[0:2] >= (3, 5):
    @pytest.fixture
    def starlette_app_async_def(starlette_api_spec_dir):
        app = StarletteApp(__name__, port=5001,
                         specification_dir=starlette_api_spec_dir,
                         debug=True)
        app.add_api('swagger_simple_async_def.yaml', validate_responses=True)
        return app


    def test_validate_responses_async_def(starlette_app_async_def):
        app_client = TestClient(starlette_app_async_def.app)
        get_bye = app_client.get('/v1.0/starlette_validate_responses')
        assert get_bye.status_code == 200
        assert get_bye.content == b'{"validate": true}'
