import sys

import pytest
import yaml
from connexion import AioHttpApp

from conftest import TEST_FOLDER

try:
    import ujson as json
except ImportError:
    import json


@pytest.fixture
def aiohttp_app(aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    options = {"validate_responses": True}
    app.add_api('swagger_simple.yaml', validate_responses=True, pass_context_arg_name='request_ctx', options=options)
    return app


async def test_app(aiohttp_app, aiohttp_client):
    # Create the app and run the test_app testcase below.
    app_client = await aiohttp_client(aiohttp_app.app)
    get_bye = await app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (await get_bye.read()) == b'Goodbye jsantos'


async def test_app_with_relative_path(aiohttp_api_spec_dir, aiohttp_client):
    # Create the app with a relative path and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir='..' /
                                       aiohttp_api_spec_dir.relative_to(TEST_FOLDER),
                     debug=True)
    app.add_api('swagger_simple.yaml')
    app_client = await aiohttp_client(app.app)
    get_bye = await app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (await get_bye.read()) == b'Goodbye jsantos'


async def test_swagger_json(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger.json file is returned for default setting passed to app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_json = await app_client.get('/v1.0/swagger.json')

    assert swagger_json.status == 200
    json_ = await swagger_json.json()
    assert api.specification.raw == json_


async def test_swagger_yaml(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger.yaml file is returned for default setting passed to app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    spec_response = await app_client.get('/v1.0/swagger.yaml')
    data_ = await spec_response.read()

    assert spec_response.status == 200
    assert api.specification.raw == yaml.load(data_)


async def test_no_swagger_json(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    options = {"swagger_json": False}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_json = await app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status == 404


async def test_no_swagger_yaml(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    options = {"swagger_json": False}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    spec_response = await app_client.get('/v1.0/swagger.yaml')  # type: flask.Response
    assert spec_response.status == 404


async def test_swagger_ui(aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui = await app_client.get('/v1.0/ui')
    assert swagger_ui.status == 200
    assert swagger_ui.url.path == '/v1.0/ui/'
    assert b'url = "/v1.0/swagger.json"' in (await swagger_ui.read())

    swagger_ui = await app_client.get('/v1.0/ui/')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (await swagger_ui.read())


async def test_swagger_ui_config_json(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger-ui-config.json file is returned for swagger_ui_config option passed to app. """
    swagger_ui_config = {"displayOperationId": True}
    options = {"swagger_ui_config": swagger_ui_config}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui_config_json = await app_client.get('/v1.0/ui/swagger-ui-config.json')
    json_ = await swagger_ui_config_json.read()

    assert swagger_ui_config_json.status == 200
    assert swagger_ui_config == json.loads(json_)


async def test_no_swagger_ui_config_json(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger-ui-config.json file is not returned when the swagger_ui_config option not passed to app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui_config_json = await app_client.get('/v1.0/ui/swagger-ui-config.json')
    assert swagger_ui_config_json.status == 404


async def test_swagger_ui_index(aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('openapi_secure.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui = await app_client.get('/v1.0/ui/index.html')
    assert swagger_ui.status == 200
    assert b'url: "/v1.0/openapi.json"' in (await swagger_ui.read())
    assert b'swagger-ui-config.json' not in (await swagger_ui.read())


async def test_swagger_ui_index_with_config(aiohttp_api_spec_dir, aiohttp_client):
    swagger_ui_config = {"displayOperationId": True}
    options = {"swagger_ui_config": swagger_ui_config}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options,
                     debug=True)
    app.add_api('openapi_secure.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui = await app_client.get('/v1.0/ui/index.html')
    assert swagger_ui.status == 200
    assert b'configUrl: "swagger-ui-config.json"' in (await swagger_ui.read())


async def test_pythonic_path_param(aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('openapi_simple.yaml', pythonic_params=True)

    app_client = await aiohttp_client(app.app)
    pythonic = await app_client.get('/v1.0/pythonic/100')
    assert pythonic.status == 200
    j = await pythonic.json()
    assert j['id_'] == 100


async def test_swagger_ui_static(aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui = await app_client.get('/v1.0/ui/lib/swagger-oauth.js')
    assert swagger_ui.status == 200

    app_client = await aiohttp_client(app.app)
    swagger_ui = await app_client.get('/v1.0/ui/swagger-ui.min.js')
    assert swagger_ui.status == 200


async def test_no_swagger_ui(aiohttp_api_spec_dir, aiohttp_client):
    options = {"swagger_ui": False}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options, debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = await aiohttp_client(app.app)
    swagger_ui = await app_client.get('/v1.0/ui/')
    assert swagger_ui.status == 404

    app2 = AioHttpApp(__name__, port=5001,
                      specification_dir=aiohttp_api_spec_dir,
                      debug=True)
    options = {"swagger_ui": False}
    app2.add_api('swagger_simple.yaml', options=options)
    app2_client = await aiohttp_client(app.app)
    swagger_ui2 = await app2_client.get('/v1.0/ui/')
    assert swagger_ui2.status == 404


async def test_middlewares(aiohttp_api_spec_dir, aiohttp_client):
    async def middleware(app, handler):
        async def middleware_handler(request):
            response = (await handler(request))
            response.body += b' middleware'
            return response

        return middleware_handler

    options = {"middlewares": [middleware]}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True, options=options)
    app.add_api('swagger_simple.yaml')
    app_client = await aiohttp_client(app.app)
    get_bye = await app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (await get_bye.read()) == b'Goodbye jsantos middleware'


async def test_response_with_str_body(aiohttp_app, aiohttp_client):
    # Create the app and run the test_app testcase below.
    app_client = await aiohttp_client(aiohttp_app.app)
    get_bye = await app_client.get('/v1.0/aiohttp_str_response')
    assert get_bye.status == 200
    assert (await get_bye.read()) == b'str response'


async def test_response_with_non_str_and_non_json_body(aiohttp_app, aiohttp_client):
    app_client = await aiohttp_client(aiohttp_app.app)
    get_bye = await app_client.get(
        '/v1.0/aiohttp_non_str_non_json_response'
    )
    assert get_bye.status == 200
    assert (await get_bye.read()) == b'1234'


async def test_response_with_bytes_body(aiohttp_app, aiohttp_client):
    # Create the app and run the test_app testcase below.
    app_client = await aiohttp_client(aiohttp_app.app)
    get_bye = await app_client.get('/v1.0/aiohttp_bytes_response')
    assert get_bye.status == 200
    assert (await get_bye.read()) == b'bytes response'


async def test_validate_responses(aiohttp_app, aiohttp_client):
    app_client = await aiohttp_client(aiohttp_app.app)
    get_bye = await app_client.get('/v1.0/aiohttp_validate_responses')
    assert get_bye.status == 200
    assert (await get_bye.json()) == {"validate": True}


async def test_get_users(aiohttp_client, aiohttp_app):
    app_client = await aiohttp_client(aiohttp_app.app)
    resp = await app_client.get('/v1.0/users')
    assert resp.url.path == '/v1.0/users/'  # followed redirect
    assert resp.status == 200

    json_data = await resp.json()
    assert json_data == \
           [{'name': 'John Doe', 'id': 1}, {'name': 'Nick Carlson', 'id': 2}]


async def test_create_user(aiohttp_client, aiohttp_app):
    app_client = await aiohttp_client(aiohttp_app.app)
    user = {'name': 'Maksim'}
    resp = await app_client.post('/v1.0/users', json=user, headers={'Content-type': 'application/json'})
    assert resp.status == 201


async def test_access_request_context(aiohttp_client, aiohttp_app):
    app_client = await aiohttp_client(aiohttp_app.app)
    resp = await app_client.post('/v1.0/aiohttp_access_request_context/')
    assert resp.status == 204


async def test_query_parsing_simple(aiohttp_client, aiohttp_app):
    expected_query = 'query'

    app_client = await aiohttp_client(aiohttp_app.app)
    resp = await app_client.get(
        '/v1.0/aiohttp_query_parsing_str',
        params={
            'query': expected_query,
        },
    )
    assert resp.status == 200

    json_data = await resp.json()
    assert json_data == {'query': expected_query}


async def test_query_parsing_array(aiohttp_client, aiohttp_app):
    expected_query = ['queryA', 'queryB']

    app_client = await aiohttp_client(aiohttp_app.app)
    resp = await app_client.get(
        '/v1.0/aiohttp_query_parsing_array',
        params={
            'query': ','.join(expected_query),
        },
    )
    assert resp.status == 200

    json_data = await resp.json()
    assert json_data == {'query': expected_query}


async def test_query_parsing_array_multi(aiohttp_client, aiohttp_app):
    expected_query = ['queryA', 'queryB', 'queryC']
    query_str = '&'.join(['query=%s' % q for q in expected_query])

    app_client = await aiohttp_client(aiohttp_app.app)
    resp = await app_client.get(
        '/v1.0/aiohttp_query_parsing_array_multi?%s' % query_str,
    )
    assert resp.status == 200

    json_data = await resp.json()
    assert json_data == {'query': expected_query}


if sys.version_info[0:2] >= (3, 5):
    @pytest.fixture
    def aiohttp_app_async_def(aiohttp_api_spec_dir):
        app = AioHttpApp(__name__, port=5001,
                         specification_dir=aiohttp_api_spec_dir,
                         debug=True)
        app.add_api('swagger_simple_async_def.yaml', validate_responses=True)
        return app


    async def test_validate_responses_async_def(aiohttp_app_async_def, aiohttp_client):
        app_client = await aiohttp_client(aiohttp_app_async_def.app)
        get_bye = await app_client.get('/v1.0/aiohttp_validate_responses')
        assert get_bye.status == 200
        assert (await get_bye.read()) == b'{"validate": true}'
