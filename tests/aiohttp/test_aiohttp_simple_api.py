import asyncio
import sys

import aiohttp.web
import pytest
from conftest import TEST_FOLDER
from connexion import AioHttpApp

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


@asyncio.coroutine
def test_app(aiohttp_app, test_client):
    # Create the app and run the test_app testcase below.
    app_client = yield from test_client(aiohttp_app.app)
    get_bye = yield from app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'Goodbye jsantos'


@asyncio.coroutine
def test_app_with_relative_path(aiohttp_api_spec_dir, test_client):
    # Create the app with a relative path and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir='..' /
                                       aiohttp_api_spec_dir.relative_to(TEST_FOLDER),
                     debug=True)
    app.add_api('swagger_simple.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'Goodbye jsantos'


@asyncio.coroutine
def test_swagger_json(aiohttp_api_spec_dir, test_client):
    """ Verify the swagger.json file is returned for default setting passed to app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = yield from test_client(app.app)
    swagger_json = yield from app_client.get('/v1.0/swagger.json')
    json_ = yield from swagger_json.read()

    assert swagger_json.status == 200
    assert api.specification.raw == json.loads(json_)


@asyncio.coroutine
def test_no_swagger_json(aiohttp_api_spec_dir, test_client):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    options = {"swagger_json": False}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options,
                     debug=True)
    api = app.add_api('swagger_simple.yaml')

    app_client = yield from test_client(app.app)
    swagger_json = yield from app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status == 404


@asyncio.coroutine
def test_swagger_ui(aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (yield from swagger_ui.read())

    swagger_ui = yield from app_client.get('/v1.0/ui/')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (yield from swagger_ui.read())


@asyncio.coroutine
def test_swagger_ui_index(aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/index.html')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (yield from swagger_ui.read())


@asyncio.coroutine
def test_swagger_ui_static(aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/lib/swagger-oauth.js')
    assert swagger_ui.status == 200

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/swagger-ui.min.js')
    assert swagger_ui.status == 200


@asyncio.coroutine
def test_no_swagger_ui(aiohttp_api_spec_dir, test_client):
    options = {"swagger_ui": False}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     options=options, debug=True)
    app.add_api('swagger_simple.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/')
    assert swagger_ui.status == 404

    app2 = AioHttpApp(__name__, port=5001,
                      specification_dir=aiohttp_api_spec_dir,
                      debug=True)
    options = {"swagger_ui": False}
    app2.add_api('swagger_simple.yaml', options=options)
    app2_client = yield from test_client(app.app)
    swagger_ui2 = yield from app2_client.get('/v1.0/ui/')
    assert swagger_ui2.status == 404


@asyncio.coroutine
def test_middlewares(aiohttp_api_spec_dir, test_client):
    @asyncio.coroutine
    def middleware(app, handler):
        @asyncio.coroutine
        def middleware_handler(request):
            response = (yield from handler(request))
            response.body += b' middleware'
            return response

        return middleware_handler

    options = {"middlewares": [middleware]}
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True, options=options)
    app.add_api('swagger_simple.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'Goodbye jsantos middleware'


@asyncio.coroutine
def test_response_with_str_body(aiohttp_app, test_client):
    # Create the app and run the test_app testcase below.
    app_client = yield from test_client(aiohttp_app.app)
    get_bye = yield from app_client.get('/v1.0/aiohttp_str_response')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'str response'


@asyncio.coroutine
def test_response_with_non_str_and_non_json_body(aiohttp_app, test_client):
    app_client = yield from test_client(aiohttp_app.app)
    get_bye = yield from app_client.get(
        '/v1.0/aiohttp_non_str_non_json_response'
    )
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'1234'


@asyncio.coroutine
def test_response_with_bytes_body(aiohttp_app, test_client):
    # Create the app and run the test_app testcase below.
    app_client = yield from test_client(aiohttp_app.app)
    get_bye = yield from app_client.get('/v1.0/aiohttp_bytes_response')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'bytes response'


@asyncio.coroutine
def test_validate_responses(aiohttp_app, test_client):
    app_client = yield from test_client(aiohttp_app.app)
    get_bye = yield from app_client.get('/v1.0/aiohttp_validate_responses')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'{"validate": true}'


@asyncio.coroutine
def test_get_users(test_client, aiohttp_app):
    app_client = yield from test_client(aiohttp_app.app)
    resp = yield from app_client.get('/v1.0/users')
    assert resp.status == 200

    json_data = yield from resp.json()
    assert json_data == \
           [{'name': 'John Doe', 'id': 1}, {'name': 'Nick Carlson', 'id': 2}]


@asyncio.coroutine
def test_create_user(test_client, aiohttp_app):
    app_client = yield from test_client(aiohttp_app.app)
    user = {'name': 'Maksim'}
    resp = yield from app_client.post('/v1.0/users', json=user, headers={'Content-type': 'application/json'})
    assert resp.status == 201


@asyncio.coroutine
def test_access_request_context(test_client, aiohttp_app):
    app_client = yield from test_client(aiohttp_app.app)
    resp = yield from app_client.post('/v1.0/aiohttp_access_request_context')
    assert resp.status == 204


@asyncio.coroutine
def test_query_parsing_simple(test_client, aiohttp_app):
    expected_query = 'query'

    app_client = yield from test_client(aiohttp_app.app)
    resp = yield from app_client.get(
        '/v1.0/aiohttp_query_parsing_str',
        params={
            'query': expected_query,
        },
    )
    assert resp.status == 200

    json_data = yield from resp.json()
    assert json_data == {'query': expected_query}


@asyncio.coroutine
def test_query_parsing_array(test_client, aiohttp_app):
    expected_query = ['queryA', 'queryB']

    app_client = yield from test_client(aiohttp_app.app)
    resp = yield from app_client.get(
        '/v1.0/aiohttp_query_parsing_array',
        params={
            'query': ','.join(expected_query),
        },
    )
    assert resp.status == 200

    json_data = yield from resp.json()
    assert json_data == {'query': expected_query}


@asyncio.coroutine
def test_query_parsing_array_multi(test_client, aiohttp_app):
    expected_query = ['queryA', 'queryB', 'queryC']
    query_str = '&'.join(['query=%s' % q for q in expected_query])

    app_client = yield from test_client(aiohttp_app.app)
    resp = yield from app_client.get(
        '/v1.0/aiohttp_query_parsing_array_multi?%s' % query_str,
    )
    assert resp.status == 200

    json_data = yield from resp.json()
    assert json_data == {'query': expected_query}


if sys.version_info[0:2] >= (3, 5):
    @pytest.fixture
    def aiohttp_app_async_def(aiohttp_api_spec_dir):
        app = AioHttpApp(__name__, port=5001,
                         specification_dir=aiohttp_api_spec_dir,
                         debug=True)
        app.add_api('swagger_simple_async_def.yaml', validate_responses=True)
        return app


    @asyncio.coroutine
    def test_validate_responses_async_def(aiohttp_app_async_def, test_client):
        app_client = yield from test_client(aiohttp_app_async_def.app)
        get_bye = yield from app_client.get('/v1.0/aiohttp_validate_responses')
        assert get_bye.status == 200
        assert (yield from get_bye.read()) == b'{"validate": true}'
