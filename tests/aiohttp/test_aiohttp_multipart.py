import asyncio
import os

import aiohttp
import pytest

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
    app.add_api(
        'openapi_multipart.yaml',
        validate_responses=True,
        strict_validation=True,
        pass_context_arg_name='request_ctx',
    )
    return app


@asyncio.coroutine
def test_single_file_upload(aiohttp_app, aiohttp_client):
    app_client = yield from aiohttp_client(aiohttp_app.app)

    resp = yield from app_client.post(
        '/v1.0/upload_file',
        data=aiohttp.FormData(fields=[('funky_funky', open(__file__, 'rb'))])(),
    )

    data = yield from resp.json()
    assert resp.status == 200
    assert data['fileName'] == f'{__name__}.py'


@asyncio.coroutine
def test_many_files_upload(aiohttp_app, aiohttp_client):
    app_client = yield from aiohttp_client(aiohttp_app.app)

    files_field = [('files', open(f, 'rb')) for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.py')]
    form_data = aiohttp.FormData(fields=files_field)

    resp = yield from app_client.post(
        '/v1.0/upload_files',
        data=form_data(),
    )

    data = yield from resp.json()

    assert resp.status == 200
    assert data['filesCount'] == len(files_field)


@asyncio.coroutine
def test_mixed_multipart(aiohttp_app, aiohttp_client):
    app_client = yield from aiohttp_client(aiohttp_app.app)

    files_field = [('files', open(f, 'rb')) for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.py')]
    form_data = aiohttp.FormData(fields=files_field)
    form_data.add_field('dir', os.path.dirname(__file__))
    form_data.add_field('testCount', str(len(files_field)))
    form_data.add_field('isRequired', 'True')

    resp = yield from app_client.post(
        '/v1.0/mixed',
        data=form_data(),
    )

    data = yield from resp.json()

    assert resp.status == 200
    assert data['filesCount'] == len(files_field)