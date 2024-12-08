from connexion.datastructures import NoContent
from connexion.mock import MockResolver
from connexion.operations import OpenAPIOperation


def test_mock_resolver_default():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "content": {
                "application/json": {
                    "examples": {"super_cool_example": {"value": {"foo": "bar"}}}
                }
            }
        }
    }

    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_numeric():
    resolver = MockResolver(mock_all=True)

    responses = {
        "200": {
            "content": {
                "application/json": {
                    "examples": {"super_cool_example": {"value": {"foo": "bar"}}}
                }
            }
        }
    }

    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_inline_schema_example():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"foo": {"schema": {"type": "string"}}},
                    },
                    "example": {"foo": "bar"},
                }
            }
        }
    }

    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_no_content():
    resolver = MockResolver(mock_all=True)

    responses = {"204": {}}

    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 204
    assert response == NoContent


def test_mock_resolver_no_examples():
    resolver = MockResolver(mock_all=True)

    responses = {"418": {}}

    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 418
    assert response == "No example response or response schema defined."


def test_mock_resolver_notimplemented():
    resolver = MockResolver(mock_all=False)

    responses = {"418": {}}

    # do not mock the existent functions
    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"operationId": "fakeapi.hello.get"},
        resolver=resolver,
    )
    assert operation.operation_id == "fakeapi.hello.get"

    # mock only the nonexistent ones
    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "operationId": "fakeapi.hello.nonexistent_function",
            "responses": responses,
        },
        resolver=resolver,
    )
    # check if it is using the mock function
    assert operation._resolution.function() == (
        "No example response or response schema defined.",
        418,
    )
