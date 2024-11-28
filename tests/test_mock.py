from connexion.datastructures import NoContent
from connexion.mock import MockResolver
from connexion.operations import OpenAPIOperation, Swagger2Operation


def test_mock_resolver_default():
    resolver = MockResolver(mock_all=True)

    responses = {"default": {"examples": {"application/json": {"foo": "bar"}}}}

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_numeric():
    resolver = MockResolver(mock_all=True)

    responses = {"200": {"examples": {"application/json": {"foo": "bar"}}}}

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_example():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "schema": {
                "type": "object",
                "properties": {"foo": {"type": "string"}},
                "example": {"foo": "bar"},
            }
        }
    }

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_example_nested_in_object():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "schema": {
                "type": "object",
                "properties": {"foo": {"type": "string", "example": "bar"}},
            }
        }
    }

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {"foo": "bar"}


def test_mock_resolver_example_nested_in_list():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "schema": {
                "type": "array",
                "items": {"type": "string", "example": "bar"},
            }
        }
    }

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == ["bar"]


def test_mock_resolver_example_nested_in_object_openapi():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"foo": {"type": "string", "example": "bar"}},
                    }
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


def test_mock_resolver_example_nested_in_list_openapi():
    resolver = MockResolver(mock_all=True)

    responses = {
        "default": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {"type": "string", "example": "bar"},
                    }
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
    assert response == ["bar"]


def test_mock_resolver_no_example_nested_in_object():
    resolver = MockResolver(mock_all=True)

    responses = {
        "200": {
            "schema": {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "string",
                    }
                },
            }
        }
    }

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert isinstance(response, dict)
    assert isinstance(response["foo"], str)


def test_mock_resolver_no_example_nested_in_list_openapi():
    resolver = MockResolver(mock_all=True)

    responses = {
        "202": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    }
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
    assert status_code == 202
    assert isinstance(response, list)
    assert all(isinstance(c, str) for c in response)


def test_mock_resolver_no_content():
    resolver = MockResolver(mock_all=True)

    responses = {"204": {}}

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "mock-1"

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 204
    assert response == NoContent


def test_mock_resolver_no_examples():
    resolver = MockResolver(mock_all=True)

    responses = {"418": {}}

    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"responses": responses},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
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
    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={"operationId": "fakeapi.hello.get"},
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )
    assert operation.operation_id == "fakeapi.hello.get"

    # mock only the nonexistent ones
    operation = Swagger2Operation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "operationId": "fakeapi.hello.nonexistent_function",
            "responses": responses,
        },
        app_produces=["application/json"],
        app_consumes=["application/json"],
        definitions={},
        resolver=resolver,
    )

    # check if it is using the mock function
    assert operation._resolution.function() == (
        "No example response or response schema defined.",
        418,
    )
