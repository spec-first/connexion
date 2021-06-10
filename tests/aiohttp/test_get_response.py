import json

import pytest
from aiohttp import web
from connexion.apis.aiohttp_api import AioHttpApi
from connexion.lifecycle import ConnexionResponse


@pytest.fixture(scope='module')
def api(aiohttp_api_spec_dir):
    yield AioHttpApi(specification=aiohttp_api_spec_dir / 'swagger_secure.yaml')


async def test_get_response_from_aiohttp_response(api):
    response = await api.get_response(web.Response(text='foo', status=201, headers={'X-header': 'value'}))
    assert isinstance(response, web.Response)
    assert response.status == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_response_from_aiohttp_stream_response(api):
    response = await api.get_response(web.StreamResponse(status=201, headers={'X-header': 'value'}))
    assert isinstance(response, web.StreamResponse)
    assert response.status == 201
    assert response.content_type == 'application/octet-stream'
    assert dict(response.headers) == {'X-header': 'value'}


async def test_get_response_from_connexion_response(api):
    response = await api.get_response(ConnexionResponse(status_code=201, mimetype='text/plain', body='foo', headers={'X-header': 'value'}))
    assert isinstance(response, web.Response)
    assert response.status == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_response_from_string(api):
    response = await api.get_response('foo')
    assert isinstance(response, web.Response)
    assert response.status == 200
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8'}


async def test_get_response_from_string_tuple(api):
    response = await api.get_response(('foo',))
    assert isinstance(response, web.Response)
    assert response.status == 200
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8'}


async def test_get_response_from_string_status(api):
    response = await api.get_response(('foo', 201))
    assert isinstance(response, web.Response)
    assert response.status == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8'}


async def test_get_response_from_string_headers(api):
    response = await api.get_response(('foo', {'X-header': 'value'}))
    assert isinstance(response, web.Response)
    assert response.status == 200
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_response_from_string_status_headers(api):
    response = await api.get_response(('foo', 201, {'X-header': 'value'}))
    assert isinstance(response, web.Response)
    assert response.status == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_response_from_tuple_error(api):
    with pytest.raises(TypeError) as e:
        await api.get_response((web.Response(text='foo', status=201, headers={'X-header': 'value'}), 200))
    assert str(e.value) == "Cannot return web.StreamResponse in tuple. Only raw data can be returned in tuple."


async def test_get_response_from_dict(api):
    response = await api.get_response({'foo': 'bar'})
    assert isinstance(response, web.Response)
    assert response.status == 200
    # odd, yes. but backwards compatible. see test_response_with_non_str_and_non_json_body in tests/aiohttp/test_aiohttp_simple_api.py
    # TODO: This should be made into JSON when aiohttp and flask serialization can be harmonized.
    assert response.body == b"{'foo': 'bar'}"
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8'}


async def test_get_response_from_dict_json(api):
    response = await api.get_response({'foo': 'bar'}, mimetype='application/json')
    assert isinstance(response, web.Response)
    assert response.status == 200
    assert json.loads(response.body.decode()) == {"foo": "bar"}
    assert response.content_type == 'application/json'
    assert dict(response.headers) == {'Content-Type': 'application/json; charset=utf-8'}


async def test_get_response_no_data(api):
    response = await api.get_response(None, mimetype='application/json')
    assert isinstance(response, web.Response)
    assert response.status == 204
    assert response.body is None
    assert response.content_type == 'application/json'
    assert dict(response.headers) == {'Content-Type': 'application/json'}


async def test_get_response_binary_json(api):
    response = await api.get_response(b'{"foo":"bar"}', mimetype='application/json')
    assert isinstance(response, web.Response)
    assert response.status == 200
    assert json.loads(response.body.decode()) == {"foo": "bar"}
    assert response.content_type == 'application/json'
    assert dict(response.headers) == {'Content-Type': 'application/json'}


async def test_get_response_binary_no_mimetype(api):
    response = await api.get_response(b'{"foo":"bar"}')
    assert isinstance(response, web.Response)
    assert response.status == 200
    assert response.body == b'{"foo":"bar"}'
    assert response.content_type == 'application/octet-stream'
    assert dict(response.headers) == {}


async def test_get_connexion_response_from_aiohttp_response(api):
    response = api.get_connexion_response(web.Response(text='foo', status=201, headers={'X-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_connexion_response_from_connexion_response(api):
    response = api.get_connexion_response(ConnexionResponse(status_code=201, content_type='text/plain', body='foo', headers={'X-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_connexion_response_from_tuple(api):
    response = api.get_connexion_response(('foo', 201, {'X-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'Content-Type': 'text/plain; charset=utf-8', 'X-header': 'value'}


async def test_get_connexion_response_from_aiohttp_stream_response(api):
    response = api.get_connexion_response(web.StreamResponse(status=201, headers={'X-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == None
    assert response.content_type == 'application/octet-stream'
    assert dict(response.headers) == {'X-header': 'value'}
