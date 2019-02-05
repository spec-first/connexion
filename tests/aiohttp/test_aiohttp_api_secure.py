import asyncio
import base64

import pytest
from connexion import AioHttpApp
from mock import MagicMock


class FakeAioHttpClientResponse(object):
    def __init__(self, status_code, data):
        """
        :type status_code: int
        :type data: dict
        """
        self.status = status_code
        self.data = data
        self.ok = status_code == 200

    @asyncio.coroutine
    def json(self):
        return self.data


@pytest.fixture
def oauth_aiohttp_client(monkeypatch):
    @asyncio.coroutine
    def fake_get(url, params=None, headers=None, timeout=None):
        """
        :type url: str
        :type params: dict| None
        """
        headers = headers or {}
        assert url == "https://oauth.example/token_info"
        token = headers.get('Authorization', 'invalid').split()[-1]
        if token in ["100", "has_myscope"]:
            return FakeAioHttpClientResponse(200, {"uid": "test-user", "scope": ["myscope"]})
        elif token in ["200", "has_wrongscope"]:
            return FakeAioHttpClientResponse(200, {"uid": "test-user", "scope": ["wrongscope"]})
        elif token == "has_myscope_otherscope":
            return FakeAioHttpClientResponse(200, {"uid": "test-user", "scope": ["myscope", "otherscope"]})
        elif token in ["300", "is_not_invalid"]:
            return FakeAioHttpClientResponse(404, {})
        elif token == "has_scopes_in_scopes_with_s":
            return FakeAioHttpClientResponse(200, {"uid": "test-user", "scopes": ["myscope", "otherscope"]})
        else:
            raise AssertionError('Not supported test token ' + token)

    client_instance = MagicMock()
    client_instance.get = fake_get
    monkeypatch.setattr('aiohttp.ClientSession', MagicMock(return_value=client_instance))


@asyncio.coroutine
def test_auth_all_paths(oauth_aiohttp_client, aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True, auth_all_paths=True)
    app.add_api('swagger_secure.yaml')

    app_client = yield from aiohttp_client(app.app)

    get_inexistent_endpoint = yield from app_client.get(
        '/v1.0/does-not-exist-valid-token',
        headers={'Authorization': 'Bearer 100'}
    )
    assert get_inexistent_endpoint.status == 404
    assert get_inexistent_endpoint.content_type == 'application/problem+json'

    get_inexistent_endpoint = yield from app_client.get(
        '/v1.0/does-not-exist-no-token'
    )
    assert get_inexistent_endpoint.status == 401
    assert get_inexistent_endpoint.content_type == 'application/problem+json'


@pytest.mark.parametrize('spec', ['swagger_secure.yaml', 'openapi_secure.yaml'])
@asyncio.coroutine
def test_secure_app(oauth_aiohttp_client, aiohttp_api_spec_dir, aiohttp_client, spec):
    """
    Test common authentication method between Swagger 2 and OpenApi 3
    """
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True)
    app.add_api(spec)
    app_client = yield from aiohttp_client(app.app)

    response = yield from app_client.get('/v1.0/all_auth')
    assert response.status == 401
    assert response.content_type == 'application/problem+json'

    response = yield from app_client.get('/v1.0/all_auth', headers={'Authorization': 'Bearer 100'})
    assert response.status == 200
    assert (yield from response.json()) == {"scope": ['myscope'], "uid": 'test-user'}

    response = yield from app_client.get('/v1.0/all_auth', headers={'authorization': 'Bearer 100'})
    assert response.status == 200, "Authorization header in lower case should be accepted"
    assert (yield from response.json()) == {"scope": ['myscope'], "uid": 'test-user'}

    response = yield from app_client.get('/v1.0/all_auth', headers={'AUTHORIZATION': 'Bearer 100'})
    assert response.status == 200, "Authorization header in upper case should be accepted"
    assert (yield from response.json()) == {"scope": ['myscope'], "uid": 'test-user'}

    basic_header = 'Basic ' + base64.b64encode(b'username:username').decode('ascii')
    response = yield from app_client.get('/v1.0/all_auth', headers={'Authorization': basic_header})
    assert response.status == 200
    assert (yield from response.json()) == {"uid": 'username'}

    basic_header = 'Basic ' + base64.b64encode(b'username:wrong').decode('ascii')
    response = yield from app_client.get('/v1.0/all_auth', headers={'Authorization': basic_header})
    assert response.status == 401, "Wrong password should trigger unauthorized"
    assert response.content_type == 'application/problem+json'

    response = yield from app_client.get('/v1.0/all_auth', headers={'X-API-Key': '{"foo": "bar"}'})
    assert response.status == 200
    assert (yield from response.json()) == {"foo": "bar"}


@asyncio.coroutine
def test_bearer_secure(aiohttp_api_spec_dir, aiohttp_client):
    """
    Test authentication method specific to OpenApi 3
    """
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True)
    app.add_api('openapi_secure.yaml')
    app_client = yield from aiohttp_client(app.app)

    bearer_header = 'Bearer {"scope": ["myscope"], "uid": "test-user"}'
    response = yield from app_client.get('/v1.0/bearer_auth', headers={'Authorization': bearer_header})
    assert response.status == 200
    assert (yield from response.json()) == {"scope": ['myscope'], "uid": 'test-user'}


@asyncio.coroutine
def test_async_secure(aiohttp_api_spec_dir, aiohttp_client):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True)
    app.add_api('openapi_secure.yaml', pass_context_arg_name='request')
    app_client = yield from aiohttp_client(app.app)

    response = yield from app_client.get('/v1.0/async_auth')
    assert response.status == 401
    assert response.content_type == 'application/problem+json'

    bearer_header = 'Bearer {"scope": ["myscope"], "uid": "test-user"}'
    response = yield from app_client.get('/v1.0/async_auth', headers={'Authorization': bearer_header})
    assert response.status == 200
    assert (yield from response.json()) == {"scope": ['myscope'], "uid": 'test-user'}

    bearer_header = 'Bearer {"scope": ["myscope", "other_scope"], "uid": "test-user"}'
    response = yield from app_client.get('/v1.0/async_auth', headers={'Authorization': bearer_header})
    assert response.status == 403, "async_scope_validation should deny access if scopes are not strictly the same"

    basic_header = 'Basic ' + base64.b64encode(b'username:username').decode('ascii')
    response = yield from app_client.get('/v1.0/async_auth', headers={'Authorization': basic_header})
    assert response.status == 200
    assert (yield from response.json()) == {"uid": 'username'}

    basic_header = 'Basic ' + base64.b64encode(b'username:wrong').decode('ascii')
    response = yield from app_client.get('/v1.0/async_auth', headers={'Authorization': basic_header})
    assert response.status == 401, "Wrong password should trigger unauthorized"
    assert response.content_type == 'application/problem+json'

    response = yield from app_client.get('/v1.0/all_auth', headers={'X-API-Key': '{"foo": "bar"}'})
    assert response.status == 200
    assert (yield from response.json()) == {"foo": "bar"}

    bearer_header = 'Bearer {"scope": ["myscope"], "uid": "test-user"}'
    response = yield from app_client.get('/v1.0/async_bearer_auth', headers={'Authorization': bearer_header})
    assert response.status == 200
    assert (yield from response.json()) == {"scope": ['myscope'], "uid": 'test-user'}
