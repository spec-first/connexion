#!/usr/bin/env python3
import datetime
import logging

#
# Source functions from fakeapi.hello
#
import sys
import uuid
from inspect import getmembers, isfunction

from sanic.request import Request
from sanic.response import HTTPResponse, json

import fakeapi.hello
from connexion import NoContent, ProblemException, context, request
from connexion.lifecycle import ConnexionResponse

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

this = sys.modules[__name__]

for fname, f in getmembers(fakeapi.hello, isfunction):

    async def tmp(request, *a, __hidden=f, **k):
        return __hidden(*a, **k)

    tmp.__name__ = fname
    setattr(this, fname, tmp)
    setattr(this, "sanic_" + fname, tmp)
    log.debug("Adding fakeapi.hello %s for sanic: %r to %r", fname, tmp, this)


async def get_bye(request, name):
    return HTTPResponse(body="Goodbye {}".format(name).encode())


async def sanic_str_response(request):
    return "str response"


async def sanic_non_str_non_json_response(request):
    return 1234


async def sanic_bytes_response(request):
    return b"bytes response"


async def sanic_validate_responses(request):
    return {"validate": True}


async def sanic_post_greeting(request, name, **kwargs):
    data = {"greeting": "Hello {name}".format(name=name)}
    return data


async def get_flask_response_tuple(request):
    return json({"foo": "bar"}), 201


async def sanic_echo(request, **kwargs):
    return json(data=kwargs, status=200)


async def sanic_access_request_context(request_ctx):
    assert request_ctx is not None
    assert isinstance(request_ctx, Request)
    return None


async def test_no_content_response(request):
    return NoContent, 204


async def sanic_query_parsing_str(request, query):
    return {"query": query}


async def sanic_query_parsing_array(request, query):
    return {"query": query}


async def sanic_query_parsing_array_multi(request, query):
    return {"query": query}


USERS = [{"id": 1, "name": "John Doe"}, {"id": 2, "name": "Nick Carlson"}]


async def sanic_users_get(request, *args):
    return json(data=USERS, status=200)


async def sanic_users_post(request, user):
    if "name" not in user:
        return ConnexionResponse(
            body={"error": "name is undefined"},
            status_code=400,
            content_type="application/json",
        )
    user["id"] = len(USERS) + 1
    USERS.append(user)
    return json(data=USERS[-1], status=201)


class DummyClass(object):
    @classmethod
    async def test_classmethod(cls, request):
        return cls.__name__

    async def test_method(self, request):
        return self.__class__.__name__


class_instance = DummyClass()  # noqa
