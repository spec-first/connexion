#!/usr/bin/env python3
import asyncio

import aiohttp
from aiohttp.web import Response as AioHttpResponse

from connexion.lifecycle import ConnexionResponse


@asyncio.coroutine
def get_bye(name):
    return AioHttpResponse(text='Goodbye {}'.format(name))


@asyncio.coroutine
def aiohttp_str_response():
    return ConnexionResponse(body='str response')


@asyncio.coroutine
def aiohttp_non_str_non_json_response():
    return ConnexionResponse(body=1234)


@asyncio.coroutine
def aiohttp_bytes_response():
    return ConnexionResponse(body=b'bytes response')


@asyncio.coroutine
def aiohttp_validate_responses():
    return ConnexionResponse(body=b'{"validate": true}')


@asyncio.coroutine
def aiohttp_post_greeting(name, **kwargs):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return ConnexionResponse(body=data)


USERS = [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Nick Carlson"}
]


@asyncio.coroutine
def aiohttp_users_get(*args):
    return aiohttp.web.json_response(data=USERS, status=200)


@asyncio.coroutine
def aiohttp_users_post(request):
    data = yield from request.json()
    if "user_name" not in data:
        return ConnexionResponse(body={"error": "user_name is undefined"},
                                 status_code=400,
                                 content_type='application/json')
    USERS.append({**data, 'id': len(USERS) + 1})
    return aiohttp.web.json_response(data=USERS[-1], status=201)
