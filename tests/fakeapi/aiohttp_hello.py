#!/usr/bin/env python3
import asyncio

import flask
from flask import jsonify, redirect

import connexion
from aiohttp.web import Response as AioHttpResponse
from connexion import NoContent, ProblemException, problem
from connexion.lifecycle import ConnexionResponse


@asyncio.coroutine
def get_bye(name):
    return AioHttpResponse(
        text='Goodbye {}'.format(name)
    )


@asyncio.coroutine
def aiohttp_str_response():
    return ConnexionResponse(
        body='str response'
    )


@asyncio.coroutine
def aiohttp_non_str_non_json_response():
    return ConnexionResponse(
        body=1234
    )


@asyncio.coroutine
def aiohttp_bytes_response():
    return ConnexionResponse(
        body=b'bytes response'
    )


@asyncio.coroutine
def aiohttp_validate_responses():
    return ConnexionResponse(
        body=b'{"validate": true}'
    )


@asyncio.coroutine
def post_greeting(name, **kwargs):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return ConnexionResponse(
        body=data
    )
