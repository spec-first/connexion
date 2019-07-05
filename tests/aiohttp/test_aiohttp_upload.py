import asyncio

import aiohttp
from aiohttp import hdrs
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

    assert resp.status == 200
