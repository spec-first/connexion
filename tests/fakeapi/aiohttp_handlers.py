#!/usr/bin/env python3
import asyncio

import aiohttp
from aiohttp.web import Request
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


@asyncio.coroutine
def aiohttp_access_request_context(request_ctx):
    assert request_ctx is not None
    assert isinstance(request_ctx, aiohttp.web.Request)
    return ConnexionResponse(status_code=204)


@asyncio.coroutine
def aiohttp_query_parsing_str(query):
    return ConnexionResponse(body={'query': query})


@asyncio.coroutine
def aiohttp_query_parsing_array(query):
    return ConnexionResponse(body={'query': query})


@asyncio.coroutine
def aiohttp_query_parsing_array_multi(query):
    return ConnexionResponse(body={'query': query})


USERS = [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Nick Carlson"}
]


@asyncio.coroutine
def aiohttp_users_get(*args):
    return aiohttp.web.json_response(data=USERS, status=200)


@asyncio.coroutine
def aiohttp_users_post(user):
    if "name" not in user:
        return ConnexionResponse(body={"error": "name is undefined"},
                                 status_code=400,
                                 content_type='application/json')
    user['id'] = len(USERS) + 1
    USERS.append(user)
    return aiohttp.web.json_response(data=USERS[-1], status=201)


@asyncio.coroutine
def aiohttp_multipart(*args, **kwargs):
    return AioHttpResponse()
