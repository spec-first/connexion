def fix_data(data):
    return data.replace(b'\\"', b'"')


def test_errors(problem_app):
    app_client = problem_app.test_client()

    greeting404 = app_client.get("/v1.0/greeting")
    assert greeting404.headers.get("content-type") == "application/problem+json"
    assert greeting404.status_code == 404
    error404 = greeting404.json()
    assert error404["type"] == "about:blank"
    assert error404["title"] == "Not Found"
    assert error404["status"] == 404
    assert "instance" not in error404

    get_greeting = app_client.get("/v1.0/greeting/jsantos")
    assert get_greeting.headers.get("content-type") == "application/problem+json"
    assert get_greeting.status_code == 405
    error405 = get_greeting.json()
    assert error405["type"] == "about:blank"
    assert error405["title"] == "Method Not Allowed"
    assert error405["status"] == 405
    assert "instance" not in error405

    get500 = app_client.get("/v1.0/except")
    assert get500.headers.get("content-type") == "application/problem+json"
    assert get500.status_code == 500
    error500 = get500.json()
    assert error500["type"] == "about:blank"
    assert error500["title"] == "Internal Server Error"
    assert (
        error500["detail"]
        == "The server encountered an internal error and was unable to complete your request. "
        "Either the server is overloaded or there is an error in the application."
    )
    assert error500["status"] == 500
    assert "instance" not in error500

    get_problem = app_client.get("/v1.0/problem")
    assert get_problem.headers.get("content-type") == "application/problem+json"
    assert get_problem.status_code == 402
    assert get_problem.headers["x-Test-Header"] == "In Test"
    error_problem = get_problem.json()
    assert error_problem["type"] == "http://www.example.com/error"
    assert error_problem["title"] == "Some Error"
    assert error_problem["detail"] == "Something went wrong somewhere"
    assert error_problem["status"] == 402
    assert error_problem["instance"] == "instance1"

    get_problem2 = app_client.get("/v1.0/other_problem")
    assert get_problem2.headers.get("content-type") == "application/problem+json"
    assert get_problem2.status_code == 402
    error_problem2 = get_problem2.json()
    assert error_problem2["type"] == "about:blank"
    assert error_problem2["title"] == "Some Error"
    assert error_problem2["detail"] == "Something went wrong somewhere"
    assert error_problem2["status"] == 402
    assert error_problem2["instance"] == "instance1"

    problematic_json = app_client.get(
        "/v1.0/json_response_with_undefined_value_to_serialize"
    )
    assert problematic_json.status_code == 500

    custom_problem = app_client.get("/v1.0/customized_problem_response")
    assert custom_problem.status_code == 403
    problem_body = custom_problem.json()
    assert "amount" in problem_body
    assert problem_body["amount"] == 23.0

    problem_as_exception = app_client.get("/v1.0/problem_exception_with_extra_args")
    assert problem_as_exception.status_code == 500
    problem_as_exception_body = problem_as_exception.json()
    assert "age" in problem_as_exception_body
    assert problem_as_exception_body["age"] == 30

    unsupported_media_type = app_client.post(
        "/v1.0/post_wrong_content_type",
        content="<html></html>",
        headers={"content-type": "text/html"},
    )
    assert unsupported_media_type.status_code == 415
    unsupported_media_type_body = unsupported_media_type.json()
    assert unsupported_media_type_body["type"] == "about:blank"
    assert unsupported_media_type_body["title"] == "Unsupported Media Type"
    assert unsupported_media_type_body["detail"].startswith(
        "Invalid Content-type (text/html)"
    )
    assert unsupported_media_type_body["status"] == 415


def test_should_raise_400_for_no_json(simple_app):
    app_client = simple_app.test_client()
    response = app_client.post("/v1.0/test-empty-object-body")
    assert response.status_code == 400
    assert response.json()["detail"] == "Request body must not be empty"
