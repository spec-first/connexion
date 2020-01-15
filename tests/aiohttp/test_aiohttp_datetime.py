import asyncio

from connexion import AioHttpApp

try:
    import ujson as json
except ImportError:
    import json


@asyncio.coroutine
def test_swagger_json(aiohttp_api_spec_dir, aiohttp_client):
    """ Verify the swagger.json file is returned for default setting passed to app. """
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=aiohttp_api_spec_dir,
                     debug=True)
    app.add_api('datetime_support.yaml')

    app_client = yield from aiohttp_client(app.app)
    swagger_json = yield from app_client.get('/v1.0/openapi.json')
    spec_data = yield from swagger_json.json()

    def get_value(data, path):
        for part in path.split('.'):
            data = data.get(part)
            assert data, "No data in part '{}' of '{}'".format(part, path)
        return data

    example = get_value(spec_data, 'paths./datetime.get.responses.200.content.application/json.schema.example.value')
    assert example in [
        '2000-01-23T04:56:07.000008+00:00',  # PyYAML 5.3
        '2000-01-23T04:56:07.000008Z'
    ]
    example = get_value(spec_data, 'paths./date.get.responses.200.content.application/json.schema.example.value')
    assert example == '2000-01-23'
    example = get_value(spec_data, 'paths./uuid.get.responses.200.content.application/json.schema.example.value')
    assert example == 'a7b8869c-5f24-4ce0-a5d1-3e44c3663aa9'

    resp = yield from app_client.get('/v1.0/datetime')
    assert resp.status == 200
    json_data = yield from resp.json()
    assert json_data == {'value': '2000-01-02T03:04:05.000006Z'}

    resp = yield from app_client.get('/v1.0/date')
    assert resp.status == 200
    json_data = yield from resp.json()
    assert json_data == {'value': '2000-01-02'}

    resp = yield from app_client.get('/v1.0/uuid')
    assert resp.status == 200
    json_data = yield from resp.json()
    assert json_data == {'value': 'e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51'}
