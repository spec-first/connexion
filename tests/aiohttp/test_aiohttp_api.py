import asyncio

import ujson
from conftest import TEST_FOLDER
from connexion import AioHttpApp


@asyncio.coroutine
def test_app(simple_aiohttp_api_spec_dir, test_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'Goodbye jsantos'


@asyncio.coroutine
def test_app_with_relative_path(simple_aiohttp_api_spec_dir,
                                      test_client):
    # Create the app with a relative path and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir='..' /
                     simple_aiohttp_api_spec_dir.relative_to(TEST_FOLDER),
                     debug=True)
    app.add_api('swagger.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'Goodbye jsantos'


@asyncio.coroutine
def test_swagger_json(simple_aiohttp_api_spec_dir, test_client):
    """ Verify the swagger.json file is returned for default setting passed to app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    api = app.add_api('swagger.yaml')

    app_client = yield from test_client(app.app)
    swagger_json = yield from app_client.get('/v1.0/swagger.json')
    json_ = yield from swagger_json.read()

    assert swagger_json.status == 200
    assert api.specification == ujson.loads(json_)


@asyncio.coroutine
def test_no_swagger_json(simple_aiohttp_api_spec_dir, test_client):
    """ Verify the swagger.json file is not returned when set to False when creating app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     swagger_json=False,
                     debug=True)
    api = app.add_api('swagger.yaml')

    app_client = yield from test_client(app.app)
    swagger_json = yield from app_client.get('/v1.0/swagger.json')  # type: flask.Response
    assert swagger_json.status == 404


@asyncio.coroutine
def test_swagger_ui(simple_aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (yield from swagger_ui.read())

    swagger_ui = yield from app_client.get('/v1.0/ui/')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (yield from swagger_ui.read())


@asyncio.coroutine
def test_swagger_ui_index(simple_aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/index.html')
    assert swagger_ui.status == 200
    assert b'url = "/v1.0/swagger.json"' in (yield from swagger_ui.read())


@asyncio.coroutine
def test_swagger_ui_static(simple_aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/lib/swagger-oauth.js')
    assert swagger_ui.status == 200

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/swagger-ui.min.js')
    assert swagger_ui.status == 200


@asyncio.coroutine
def test_no_swagger_ui(simple_aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     swagger_ui=False, debug=True)
    app.add_api('swagger.yaml')

    app_client = yield from test_client(app.app)
    swagger_ui = yield from app_client.get('/v1.0/ui/')
    assert swagger_ui.status == 404

    app2 = AioHttpApp(__name__, port=5001,
                      specification_dir=simple_aiohttp_api_spec_dir,
                      debug=True)
    app2.add_api('swagger.yaml', swagger_ui=False)
    app2_client = yield from test_client(app.app)
    swagger_ui2 = yield from app2_client.get('/v1.0/ui/')
    assert swagger_ui2.status == 404


@asyncio.coroutine
def test_middlewares(simple_aiohttp_api_spec_dir, test_client):
    @asyncio.coroutine
    def middleware(app, handler):
        @asyncio.coroutine
        def middleware_handler(request):
            response = (yield from handler(request))
            response.body += b' middleware'
            return response

        return middleware_handler

    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True, middlewares=[middleware])
    app.add_api('swagger.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/bye/jsantos')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'Goodbye jsantos middleware'


@asyncio.coroutine
def test_response_with_str_body(simple_aiohttp_api_spec_dir, test_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/aiohttp_str_response')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'str response'


@asyncio.coroutine
def test_response_with_non_str_and_non_json_body(
      simple_aiohttp_api_spec_dir, test_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get(
        '/v1.0/aiohttp_non_str_non_json_response'
    )
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'1234'


@asyncio.coroutine
def test_response_with_bytes_body(simple_aiohttp_api_spec_dir, test_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml')
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/aiohttp_bytes_response')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'bytes response'


@asyncio.coroutine
def test_validate_responses(simple_aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger.yaml', validate_responses=True)
    app_client = yield from test_client(app.app)
    get_bye = yield from app_client.get('/v1.0/aiohttp_validate_responses')
    assert get_bye.status == 200
    assert (yield from get_bye.read()) == b'{"validate": true}'
