import asyncio
import base64

from connexion import AioHttpApp


@asyncio.coroutine
def test_auth_all_paths(oauth_requests, aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True, auth_all_paths=True)
    app.add_api('swagger_secure.yaml')

    app_client = yield from aiohttp_client(app.app)

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
def test_secure_app(oauth_requests, aiohttp_api_spec_dir, aiohttp_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('swagger_secure.yaml')
    app_client = yield from aiohttp_client(app.app)

    post_hello = yield from app_client.post('/v1.0/greeting/jsantos')
    assert post_hello.status == 401

    headers = {'Authorization': 'Bearer 100'}
    post_hello = yield from app_client.post(
        '/v1.0/greeting/jsantos',
        headers=headers
    )

    assert post_hello.status == 200
    assert (yield from post_hello.json()) == {"greeting": "Hello jsantos"}

    headers = {'authorization': 'Bearer 100'}
    post_hello = yield from app_client.post(
        '/v1.0/greeting/jsantos',
        headers=headers
    )

    assert post_hello.status == 200, "Authorization header in lower case should be accepted"
    assert (yield from post_hello.json()) == {"greeting": "Hello jsantos"}

    headers = {'AUTHORIZATION': 'Bearer 100'}
    post_hello = yield from app_client.post(
        '/v1.0/greeting/jsantos',
        headers=headers
    )

    assert post_hello.status == 200, "Authorization header in upper case should be accepted"
    assert (yield from post_hello.json()) == {"greeting": "Hello jsantos"}

    no_authorization = yield from app_client.post(
        '/v1.0/greeting/jsantos',
    )

    assert no_authorization.status == 401
    assert no_authorization.content_type == 'application/problem+json'


@asyncio.coroutine
def test_basic_auth_secure(oauth_requests, aiohttp_api_spec_dir, aiohttp_client):
    # Create the app and run the test_app testcase below.
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('openapi_secure.yaml')
    app_client = yield from aiohttp_client(app.app)

    post_hello = yield from app_client.post('/v1.0/greeting/jsantos')
    assert post_hello.status == 401

    username= 'username'
    password = username  # check fake_basic_auth
    basic_header = 'Basic ' + base64.b64encode((username + ':' + password).encode('ascii')).decode('ascii')
    headers = {'Authorization': basic_header}
    post_hello = yield from app_client.post(
        '/v1.0/greeting/jsantos',
        headers=headers
    )

    assert (yield from post_hello.read()) == b"{'greeting': 'Hello jsantos'}"

    broken_header = 'Basic ' + base64.b64encode((username + ':' + password[:-1]).encode('ascii')).decode('ascii')
    headers = {'Authorization': broken_header}
    no_auth = yield from app_client.post(
        '/v1.0/greeting/jsantos',
        headers=headers
    )
    assert no_auth.status == 401, "Wrong header should result into Unauthorized"
    assert no_auth.content_type == 'application/problem+json'
