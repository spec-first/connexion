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
        pythonic_params=True,
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

    dir_name = os.path.dirname(__file__)
    files_field = [('files', open(f'{dir_name}/{file_name}', 'rb')) for file_name in os.listdir(dir_name) if file_name.endswith('.py')]

    form_data = aiohttp.FormData(fields=files_field)

    resp = yield from app_client.post(
        '/v1.0/upload_files',
        data=form_data(),
    )

    data = yield from resp.json()

    assert resp.status == 200
    assert data['filesCount'] == len(files_field)


@asyncio.coroutine
def test_mixed_multipart_single_file(aiohttp_app, aiohttp_client):
    app_client = yield from aiohttp_client(aiohttp_app.app)

    form_data = aiohttp.FormData()
    form_data.add_field('dirName', os.path.dirname(__file__))
    form_data.add_field('funky_funky', open(__file__, 'rb'))

    resp = yield from app_client.post(
        '/v1.0/mixed_single_file',
        data=form_data(),
    )

    data = yield from resp.json()

    assert resp.status == 200
    assert data['dirName'] == os.path.dirname(__file__)
    assert data['fileName'] == f'{__name__}.py'


@asyncio.coroutine
def test_mixed_multipart_many_files(aiohttp_app, aiohttp_client):
    app_client = yield from aiohttp_client(aiohttp_app.app)

    dir_name = os.path.dirname(__file__)
    files_field = [('files', open(f'{dir_name}/{file_name}', 'rb')) for file_name in os.listdir(dir_name) if file_name.endswith('.py')]

    form_data = aiohttp.FormData(fields=files_field)
    form_data.add_field('dirName', os.path.dirname(__file__))
    form_data.add_field('testCount', str(len(files_field)))

    resp = yield from app_client.post(
        '/v1.0/mixed_many_files',
        data=form_data(),
    )

    data = yield from resp.json()

    assert resp.status == 200
    assert data['dirName'] == os.path.dirname(__file__)
    assert data['testCount'] == len(files_field)
    assert data['filesCount'] == len(files_field)
