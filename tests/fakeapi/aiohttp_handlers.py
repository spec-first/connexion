#!/usr/bin/env python3
import datetime
import uuid

import aiohttp
from aiohttp.web import Request
from aiohttp.web import Response as AioHttpResponse
from connexion.lifecycle import ConnexionResponse


async def get_bye(name):
    return AioHttpResponse(text='Goodbye {}'.format(name))


async def aiohttp_str_response():
    return 'str response'


async def aiohttp_non_str_non_json_response():
    return 1234


async def aiohttp_bytes_response():
    return b'bytes response'


async def aiohttp_validate_responses():
    return {"validate": True}


async def aiohttp_post_greeting(name, **kwargs):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return data

async def aiohttp_echo(**kwargs):
    return aiohttp.web.json_response(data=kwargs, status=200)


async def aiohttp_access_request_context(request_ctx):
    assert request_ctx is not None
    assert isinstance(request_ctx, aiohttp.web.Request)
    return None


async def aiohttp_query_parsing_str(query):
    return {'query': query}


async def aiohttp_query_parsing_array(query):
    return {'query': query}


async def aiohttp_query_parsing_array_multi(query):
    return {'query': query}


USERS = [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Nick Carlson"}
]


async def aiohttp_users_get(*args):
    return aiohttp.web.json_response(data=USERS, status=200)


async def aiohttp_users_post(user):
    if "name" not in user:
        return ConnexionResponse(body={"error": "name is undefined"},
                                 status_code=400,
                                 content_type='application/json')
    user['id'] = len(USERS) + 1
    USERS.append(user)
    return aiohttp.web.json_response(data=USERS[-1], status=201)


async def get_datetime():
    return ConnexionResponse(body={'value': datetime.datetime(2000, 1, 2, 3, 4, 5, 6)})


async def get_date():
    return ConnexionResponse(body={'value': datetime.date(2000, 1, 2)})


async def get_uuid():
    return ConnexionResponse(body={'value': uuid.UUID(hex='e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51')})


@asyncio.coroutine
def aiohttp_multipart_single_file(funky_funky):
    return aiohttp.web.json_response(
        data={'fileName': funky_funky.filename},
    )


@asyncio.coroutine
def aiohttp_multipart_many_files(files):
    return aiohttp.web.json_response(
        data={'filesCount': len(files)},
    )


@asyncio.coroutine
def aiohttp_multipart_mixed_single_file(dir_name, funky_funky):
    return aiohttp.web.json_response(
        data={
            'dirName': dir_name,
            'fileName': funky_funky.filename,
        },
    )


@asyncio.coroutine
def aiohttp_multipart_mixed_many_files(dir_name, test_count, files):
    return aiohttp.web.json_response(
        data={
            'filesCount': len(files),
            'dirName': dir_name,
            'testCount': test_count,
        },
    )
