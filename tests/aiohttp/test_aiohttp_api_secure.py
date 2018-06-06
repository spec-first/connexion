import asyncio

import ujson
from conftest import TEST_FOLDER
from connexion import AioHttpApp


@asyncio.coroutine
def test_auth_all_paths(oauth_requests, aiohttp_api_spec_dir, test_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True, auth_all_paths=True)
    app.add_api('swagger_secure.yaml')

    app_client = yield from test_client(app.app)

    headers = {'Authorization': 'Bearer 100'}
    get_inexistent_endpoint = yield from app_client.get(
        '/v1.0/does-not-exist-valid-token',
        headers=headers
    )
    assert get_inexistent_endpoint.status == 404
    assert get_inexistent_endpoint.content_type == 'application/problem+json'

    get_inexistent_endpoint = yield from app_client.get(
        '/v1.0/does-not-exist-no-token'
    )
    assert get_inexistent_endpoint.status == 401
    assert get_inexistent_endpoint.content_type == 'application/problem+json'


@asyncio.coroutine
def test_secure_app(oauth_requests, aiohttp_api_spec_dir, test_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_secure.yaml')
    app_client = yield from test_client(app.app)

    post_hello = yield from app_client.post('/v1.0/greeting/jsantos')
    assert post_hello.status == 401

    headers = {'Authorization': 'Bearer 100'}
    post_hello = yield from app_client.post(
        '/v1.0/greeting/jsantos',
        headers=headers
    )

    assert post_hello.status == 200
    assert (yield from post_hello.read()) == b'{"greeting":"Hello jsantos"}'
