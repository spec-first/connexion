#!/usr/bin/env python3
import datetime
import uuid

from connexion.lifecycle import ConnexionResponse

from starlette.requests import Request
from starlette.responses import PlainTextResponse as StarletteResponse, JSONResponse


async def get_bye(name):
    return StarletteResponse(content=f'Goodbye {name}')


async def starlette_str_response():
    return 'str response'


async def starlette_non_str_non_json_response():
    return 1234


async def starlette_bytes_response():
    return b'bytes response'


async def starlette_validate_responses():
    return {"validate": True}


async def starlette_post_greeting(name, **kwargs):
    data = {'greeting': f'Hello {name}'}
    return data

async def starlette_echo(**kwargs):
    return JSONResponse(content=kwargs, status_code=200)


async def starlette_access_request_context(request_ctx):
    assert request_ctx is not None
    assert isinstance(request_ctx, Request)
    return None


async def starlette_query_parsing_str(query):
    return {'query': query}


async def starlette_query_parsing_array(query):
    return {'query': query}


async def starlette_query_parsing_array_multi(query):
    return {'query': query}


USERS = [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Nick Carlson"}
]


async def starlette_users_get(*args):
    return JSONResponse(content=USERS, status_code=200)


async def starlette_users_post(user):
    if "name" not in user:
        return ConnexionResponse(body={"error": "name is undefined"},
                                 status_code=400,
                                 content_type='application/json')
    user['id'] = len(USERS) + 1
    USERS.append(user)
    return JSONResponse(content=USERS[-1], status_code=201)


async def starlette_token_info(token_info):
    return JSONResponse(content=token_info)


async def starlette_all_auth(token_info):
    return await starlette_token_info(token_info)


async def starlette_async_auth(token_info):
    return await starlette_token_info(token_info)


async def starlette_bearer_auth(token_info):
    return await starlette_token_info(token_info)


async def starlette_async_bearer_auth(token_info):
    return await starlette_token_info(token_info)


async def get_datetime():
    return ConnexionResponse(body={'value': datetime.datetime(2000, 1, 2, 3, 4, 5, 6)})


async def get_date():
    return ConnexionResponse(body={'value': datetime.date(2000, 1, 2)})


async def get_uuid():
    return ConnexionResponse(body={'value': uuid.UUID(hex='e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51')})
