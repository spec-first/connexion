import json

import pytest
from connexion.apis.starlette_api import StarletteApi
from connexion.lifecycle import ConnexionResponse
from starlette.responses import Response, StreamingResponse, PlainTextResponse



@pytest.fixture(scope='module')
def api(starlette_api_spec_dir):
    yield StarletteApi(specification=starlette_api_spec_dir / 'swagger_secure.yaml')


@pytest.mark.asyncio
async def test_get_response_from_starlette_response(api):
    response = await api.get_response(PlainTextResponse(content='foo', status_code=201, headers={'x-header': 'value'}))
    assert isinstance(response, Response)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_starlette_stream_response(api):
    response = await api.get_response(StreamingResponse([], status_code=201, headers={'x-header': 'value'}))
    assert isinstance(response, StreamingResponse)
    assert response.status_code == 201
    assert dict(response.headers) == {'x-header': 'value'}


@pytest.mark.asyncio
async def test_get_response_from_connexion_response(api):
    response = await api.get_response(ConnexionResponse(status_code=201, mimetype='text/plain', body='foo', headers={'x-header': 'value'}))
    assert isinstance(response, Response)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_string(api):
    response = await api.get_response('foo')
    print(response.headers)
    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_string_tuple(api):
    response = await api.get_response(('foo',))
    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_string_status(api):
    response = await api.get_response(('foo', 201))
    assert isinstance(response, Response)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_string_headers(api):
    response = await api.get_response(('foo', {'x-header': 'value'}))
    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_string_status_headers(api):
    response = await api.get_response(('foo', 201, {'x-header': 'value'}))
    assert isinstance(response, Response)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_response_from_tuple_error(api):
    with pytest.raises(TypeError) as e:
        await api.get_response((Response(content='foo', status_code=201, headers={'x-header': 'value'}), 200))
    assert str(e.value) == "Cannot return starlette.responses.Response in tuple. Only raw data can be returned in tuple."


@pytest.mark.asyncio
async def test_get_response_from_dict(api):
    response = await api.get_response({'foo': 'bar'})
    assert isinstance(response, Response)
    assert response.status_code== 200
    # odd, yes. but backwards compatible. see test_response_with_non_str_and_non_json_body in tests/aiohttp/test_aiohttp_simple_api.py
    # TODO: This should be made into JSON when aiohttp and flask serialization can be harmonized.
    assert response.body == b"{'foo': 'bar'}"
    assert response.media_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'content-length': '14'}


@pytest.mark.asyncio
async def test_get_response_from_dict_json(api):
    response = await api.get_response({'foo': 'bar'}, mimetype='application/json')
    assert isinstance(response, Response)
    assert response.status_code== 200
    assert json.loads(response.body.decode()) == {"foo": "bar"}
    assert response.body == b'{"foo": "bar"}\n'
    assert response.media_type == 'application/json'
    assert dict(response.headers) == {'content-type': 'application/json', 'content-length': '15'}


@pytest.mark.asyncio
async def test_get_response_no_data(api):
    response = await api.get_response(None, mimetype='application/json')
    assert isinstance(response, Response)
    assert response.status_code== 204
    assert response.body == b""
    assert response.media_type == 'application/json'
    assert dict(response.headers) == {'content-type': 'application/json'}


@pytest.mark.asyncio
async def test_get_response_binary_json(api):
    response = await api.get_response(b'{"foo":"bar"}', mimetype='application/json')
    assert isinstance(response, Response)
    assert response.status_code== 200
    assert json.loads(response.body.decode()) == {"foo": "bar"}
    assert response.media_type == 'application/json'
    assert dict(response.headers) == {'content-type': 'application/json', 'content-length': '13'}


@pytest.mark.asyncio
async def test_get_response_binary_no_mimetype(api):
    response = await api.get_response(b'{"foo":"bar"}')
    assert isinstance(response, Response)
    assert response.status_code== 200
    assert response.body == b'{"foo":"bar"}'
    assert response.media_type == 'application/octet-stream'
    assert dict(response.headers) == {'content-type': 'application/octet-stream', 'content-length': '13'}


@pytest.mark.asyncio
async def test_get_connexion_response_from_starlette_response(api):
    response = api.get_connexion_response(PlainTextResponse(content='foo', status_code=201, headers={'x-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_connexion_response_from_connexion_response(api):
    response = api.get_connexion_response(ConnexionResponse(status_code=201, content_type='text/plain', body='foo', headers={'x-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert response.content_type == 'text/plain'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_connexion_response_from_tuple(api):
    response = api.get_connexion_response(('foo', 201, {'x-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == b'foo'
    assert dict(response.headers) == {'content-type': 'text/plain; charset=utf-8', 'x-header': 'value', 'content-length': '3'}


@pytest.mark.asyncio
async def test_get_connexion_response_from_starlette_stream_response(api):
    response = api.get_connexion_response(StreamingResponse([], status_code=201, headers={'x-header': 'value'}))
    assert isinstance(response, ConnexionResponse)
    assert response.status_code == 201
    assert response.body == None
    assert dict(response.headers) == {'x-header': 'value'}
