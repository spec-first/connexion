# coding: utf-8

import asyncio

import pytest

import aiohttp.test_utils
from connexion import AioHttpApp
from connexion.apis.aiohttp_api import HTTPStatus


def is_valid_problem_json(json_body):
    return all(key in json_body for key in ["type", "title", "detail", "status"])


@pytest.fixture
def aiohttp_app(problem_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=problem_api_spec_dir,
                     debug=True)
    options = {"validate_responses": True}
    app.add_api('openapi.yaml', validate_responses=True, pass_context_arg_name='request_ctx', options=options)
    return app


@asyncio.coroutine
def test_aiohttp_problems(aiohttp_app, aiohttp_client):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = yield from aiohttp_client(aiohttp_app.app)  # type: aiohttp.test_utils.TestClient

    greeting404 = yield from app_client.get('/v1.0/greeting')  # type: aiohttp.ClientResponse
    assert greeting404.content_type == 'application/problem+json'
    assert greeting404.status == 404
    error404 = yield from greeting404.json()
    assert is_valid_problem_json(error404)
    assert error404['type'] == 'about:blank'
    assert error404['title'] == 'Not Found'
    assert error404['detail'] == HTTPStatus(404).description
    assert error404['status'] == 404
    assert 'instance' not in error404

    get_greeting = yield from app_client.get('/v1.0/greeting/jsantos')  # type: aiohttp.ClientResponse
    assert get_greeting.content_type == 'application/problem+json'
    assert get_greeting.status == 405
    error405 = yield from get_greeting.json()
    assert is_valid_problem_json(error405)
    assert error405['type'] == 'about:blank'
    assert error405['title'] == 'Method Not Allowed'
    assert error405['detail'] == HTTPStatus(405).description
    assert error405['status'] == 405
    assert 'instance' not in error405

    get500 = yield from app_client.get('/v1.0/except')  # type: aiohttp.ClientResponse
    assert get500.content_type == 'application/problem+json'
    assert get500.status == 500
    error500 = yield from get500.json()
    assert is_valid_problem_json(error500)
    assert error500['type'] == 'about:blank'
    assert error500['title'] == 'Internal Server Error'
    assert error500['detail'] == HTTPStatus(500).description
    assert error500['status'] == 500
    assert 'instance' not in error500

    get_problem = yield from app_client.get('/v1.0/problem')  # type: aiohttp.ClientResponse
    assert get_problem.content_type == 'application/problem+json'
    assert get_problem.status == 418
    assert get_problem.headers['x-Test-Header'] == 'In Test'
    error_problem = yield from get_problem.json()
    assert is_valid_problem_json(error_problem)
    assert error_problem['type'] == 'http://www.example.com/error'
    assert error_problem['title'] == 'Some Error'
    assert error_problem['detail'] == 'Something went wrong somewhere'
    assert error_problem['status'] == 418
    assert error_problem['instance'] == 'instance1'

    problematic_json = yield from app_client.get(
        '/v1.0/json_response_with_undefined_value_to_serialize')  # type: aiohttp.ClientResponse
    assert problematic_json.content_type == 'application/problem+json'
    assert problematic_json.status == 500
    problematic_json_body = yield from problematic_json.json()
    assert is_valid_problem_json(problematic_json_body)

    custom_problem = yield from app_client.get('/v1.0/customized_problem_response')  # type: aiohttp.ClientResponse
    assert custom_problem.content_type == 'application/problem+json'
    assert custom_problem.status == 403
    problem_body = yield from custom_problem.json()
    assert is_valid_problem_json(problem_body)
    assert 'amount' in problem_body

    problem_as_exception = yield from app_client.get('/v1.0/problem_exception_with_extra_args')  # type: aiohttp.ClientResponse
    assert problem_as_exception.content_type == "application/problem+json"
    assert problem_as_exception.status == 400
    problem_as_exception_body = yield from problem_as_exception.json()
    assert is_valid_problem_json(problem_as_exception_body)
    assert 'age' in problem_as_exception_body
    assert problem_as_exception_body['age'] == 30


@pytest.mark.skip(reason="aiohttp_api.get_connexion_response uses _cast_body "
                         "to stringify the dict directly instead of using json.dumps. "
                         "This differs from flask usage, where there is no _cast_body.")
@asyncio.coroutine
def test_aiohttp_problem_with_text_content_type(aiohttp_app, aiohttp_client):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = yield from aiohttp_client(aiohttp_app.app)  # type: aiohttp.test_utils.TestClient

    get_problem2 = yield from app_client.get('/v1.0/other_problem')  # type: aiohttp.ClientResponse
    assert get_problem2.content_type == 'application/problem+json'
    assert get_problem2.status == 418
    error_problem2 = yield from get_problem2.json()
    assert is_valid_problem_json(error_problem2)
    assert error_problem2['type'] == 'about:blank'
    assert error_problem2['title'] == 'Some Error'
    assert error_problem2['detail'] == 'Something went wrong somewhere'
    assert error_problem2['status'] == 418
    assert error_problem2['instance'] == 'instance1'

