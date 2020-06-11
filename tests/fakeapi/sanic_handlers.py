#!/usr/bin/env python3
import datetime
import uuid

from connexion.lifecycle import ConnexionResponse
from sanic.response import HTTPResponse, json
from sanic.request import Request


async def get_bye(request, name):
    return HTTPResponse(text='Goodbye {}'.format(name))


async def sanic_str_response(request):
    return 'str response'


async def sanic_non_str_non_json_response(request):
    return 1234


async def sanic_bytes_response(request):
    return b'bytes response'


async def sanic_validate_responses(request):
    return {"validate": True}


async def sanic_post_greeting(request, name, **kwargs):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return data


async def sanic_echo(request, **kwargs):
    return json(data=kwargs, status=200)


async def sanic_access_request_context(request_ctx):
    assert request_ctx is not None
    assert isinstance(request_ctx, Request)
    return None


async def sanic_query_parsing_str(request, query):
    return {'query': query}


async def sanic_query_parsing_array(request, query):
    return {'query': query}


async def sanic_query_parsing_array_multi(request, query):
    return {'query': query}


USERS = [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Nick Carlson"}
]


async def sanic_users_get(request, *args):
    return json(data=USERS, status=200)


async def sanic_users_post(request, user):
    if "name" not in user:
        return ConnexionResponse(body={"error": "name is undefined"},
                                 status_code=400,
                                 content_type='application/json')
    user['id'] = len(USERS) + 1
    USERS.append(user)
    return json(data=USERS[-1], status=201)


async def get_datetime(request):
    return ConnexionResponse(body={'value': datetime.datetime(2000, 1, 2, 3, 4, 5, 6)})


async def get_date(request):
    return ConnexionResponse(body={'value': datetime.date(2000, 1, 2)})


async def get_uuid(request):
    return ConnexionResponse(body={'value': uuid.UUID(hex='e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51')})


class DummyClass(object):
    @classmethod
    def test_classmethod(cls, request):
        return cls.__name__

    def test_method(self, request):
        return self.__class__.__name__

class_instance = DummyClass()  # noqa
