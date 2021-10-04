import asyncio
import pytest
from http import HTTPStatus
from connexion import StarletteApp
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

def is_valid_problem_json(json_body):
    return all(key in json_body for key in ["type", "title", "detail", "status"])


@pytest.fixture
def starlette_app(problem_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=problem_api_spec_dir,
                     debug=True)
    options = {"validate_responses": True}
    app.add_api('openapi.yaml', validate_responses=True, pass_context_arg_name='request_ctx', options=options)
    return app


def test_starlette_problems_404(starlette_app):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = TestClient(starlette_app.app)  

    greeting404 = app_client.get('/v1.0/greeting')
    assert greeting404.headers["content-type"] == 'application/problem+json'
    assert greeting404.status_code == 404
    error404 = greeting404.json()
    assert is_valid_problem_json(error404)
    assert error404['type'] == 'about:blank'
    assert error404['title'] == 'Not Found'
    assert error404['detail'] == HTTPStatus(404).description
    assert error404['status'] == 404
    assert 'instance' not in error404


def test_starlette_problems_405(starlette_app):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = TestClient(starlette_app.app)  

    get_greeting = app_client.get('/v1.0/greeting/jsantos')  
    assert get_greeting.headers["content-type"] == 'application/problem+json'
    assert get_greeting.status_code == 405
    error405 = get_greeting.json()
    assert is_valid_problem_json(error405)
    assert error405['type'] == 'about:blank'
    assert error405['title'] == 'Method Not Allowed'
    assert error405['detail'] == HTTPStatus(405).description
    assert error405['status'] == 405
    assert 'instance' not in error405


def test_starlette_problems_500(starlette_app):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = TestClient(starlette_app.app)  

    get500 = app_client.get('/v1.0/except')  
    assert get500.headers["content-type"] == 'application/problem+json'
    assert get500.status_code == 500
    error500 = get500.json()
    assert is_valid_problem_json(error500)
    assert error500['type'] == 'about:blank'
    assert error500['title'] == 'Internal Server Error'
    assert error500['detail'] == HTTPStatus(500).description
    assert error500['status'] == 500
    assert 'instance' not in error500


def test_starlette_problems_418(starlette_app):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = TestClient(starlette_app.app)  

    get_problem = app_client.get('/v1.0/problem')  
    assert get_problem.headers["content-type"] == 'application/problem+json'
    assert get_problem.status_code == 418
    assert get_problem.headers['x-Test-Header'] == 'In Test'
    error_problem = get_problem.json()
    assert is_valid_problem_json(error_problem)
    assert error_problem['type'] == 'http://www.example.com/error'
    assert error_problem['title'] == 'Some Error'
    assert error_problem['detail'] == 'Something went wrong somewhere'
    assert error_problem['status'] == 418
    assert error_problem['instance'] == 'instance1'


def test_starlette_problems_misc(starlette_app):
    # TODO: This is a based on test_errors.test_errors(). That should be refactored
    #       so that it is parameterized for all web frameworks.
    app_client = TestClient(starlette_app.app)  

    problematic_json = app_client.get(
        '/v1.0/json_response_with_undefined_value_to_serialize')  
    assert problematic_json.headers["content-type"] == 'application/problem+json'
    assert problematic_json.status_code == 500
    problematic_json_body = problematic_json.json()
    assert is_valid_problem_json(problematic_json_body)

    custom_problem = app_client.get('/v1.0/customized_problem_response')  
    assert custom_problem.headers["content-type"] == 'application/problem+json'
    assert custom_problem.status_code == 403
    problem_body = custom_problem.json()
    assert is_valid_problem_json(problem_body)
    assert 'amount' in problem_body

    problem_as_exception = app_client.get('/v1.0/problem_exception_with_extra_args')  
    assert problem_as_exception.headers["content-type"] == "application/problem+json"
    assert problem_as_exception.status_code == 400
    problem_as_exception_body = problem_as_exception.json()
    assert is_valid_problem_json(problem_as_exception_body)
    assert 'age' in problem_as_exception_body
    assert problem_as_exception_body['age'] == 30


@pytest.mark.skip(reason="starlette_api.get_connexion_response uses _cast_body "
                         "to stringify the dict directly instead of using json.dumps. "
                         "This differs from flask usage, where there is no _cast_body.")
def test_starlette_problem_with_text_content_type(starlette_app):
    app_client = TestClient(starlette_app.app)

    get_problem2 = app_client.get('/v1.0/other_problem')
    assert get_problem2.headers["content-type"] == 'application/problem+json'
    assert get_problem2.status_code == 418
    error_problem2 = get_problem2.json()
    assert is_valid_problem_json(error_problem2)
    assert error_problem2['type'] == 'about:blank'
    assert error_problem2['title'] == 'Some Error'
    assert error_problem2['detail'] == 'Something went wrong somewhere'
    assert error_problem2['status'] == 418
    assert error_problem2['instance'] == 'instance1'

