import os
from pathlib import Path

import pytest
from connexion import AioHttpApp

import aiohttp

try:
    import ujson as json
except ImportError:
    import json


@pytest.fixture
def aiohttp_app(aiohttp_api_spec_dir):
    app = AioHttpApp(
        __name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True
    )
    app.add_api(
        "openapi_multipart.yaml",
        validate_responses=True,
        strict_validation=True,
        pythonic_params=True,
        pass_context_arg_name="request_ctx",
    )
    return app


async def test_single_file_upload(aiohttp_app, aiohttp_client):
    app_client = await aiohttp_client(aiohttp_app.app)

    resp = await app_client.post(
        "/v1.0/upload_file",
        data=aiohttp.FormData(fields=[("myfile", open(__file__, "rb"))])(),
    )

    data = await resp.json()
    assert resp.status == 200
    assert data["fileName"] == f"{__name__}.py"
    assert data["myfile_content"] == Path(__file__).read_bytes().decode("utf8")


async def test_many_files_upload(aiohttp_app, aiohttp_client):
    app_client = await aiohttp_client(aiohttp_app.app)

    dir_name = os.path.dirname(__file__)
    files_field = [
        ("myfiles", open(f"{dir_name}/{file_name}", "rb"))
        for file_name in sorted(os.listdir(dir_name))
        if file_name.endswith(".py")
    ]

    form_data = aiohttp.FormData(fields=files_field)

    resp = await app_client.post(
        "/v1.0/upload_files",
        data=form_data(),
    )

    data = await resp.json()

    assert resp.status == 200
    assert data["files_count"] == len(files_field)
    assert data["myfiles_content"] == [
        Path(f"{dir_name}/{file_name}").read_bytes().decode("utf8")
        for file_name in sorted(os.listdir(dir_name))
        if file_name.endswith(".py")
    ]


async def test_mixed_multipart_single_file(aiohttp_app, aiohttp_client):
    app_client = await aiohttp_client(aiohttp_app.app)

    form_data = aiohttp.FormData()
    form_data.add_field("dir_name", os.path.dirname(__file__))
    form_data.add_field("myfile", open(__file__, "rb"))

    resp = await app_client.post(
        "/v1.0/mixed_single_file",
        data=form_data(),
    )

    data = await resp.json()

    assert resp.status == 200
    assert data["dir_name"] == os.path.dirname(__file__)
    assert data["fileName"] == f"{__name__}.py"
    assert data["myfile_content"] == Path(__file__).read_bytes().decode("utf8")


async def test_mixed_multipart_many_files(aiohttp_app, aiohttp_client):
    app_client = await aiohttp_client(aiohttp_app.app)

    dir_name = os.path.dirname(__file__)
    files_field = [
        ("myfiles", open(f"{dir_name}/{file_name}", "rb"))
        for file_name in sorted(os.listdir(dir_name))
        if file_name.endswith(".py")
    ]

    form_data = aiohttp.FormData(fields=files_field)
    form_data.add_field("dir_name", os.path.dirname(__file__))
    form_data.add_field("test_count", str(len(files_field)))

    resp = await app_client.post(
        "/v1.0/mixed_many_files",
        data=form_data(),
    )

    data = await resp.json()

    assert resp.status == 200
    assert data["dir_name"] == os.path.dirname(__file__)
    assert data["test_count"] == len(files_field)
    assert data["files_count"] == len(files_field)
    assert data["myfiles_content"] == [
        Path(f"{dir_name}/{file_name}").read_bytes().decode("utf8")
        for file_name in sorted(os.listdir(dir_name))
        if file_name.endswith(".py")
    ]
