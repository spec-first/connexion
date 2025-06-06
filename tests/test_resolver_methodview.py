from connexion.operations import OpenAPIOperation
from connexion.resolver import MethodViewResolver, Resolver

COMPONENTS = {"parameters": {"myparam": {"in": "path", "schema": {"type": "integer"}}}}


def test_standard_resolve_x_router_controller():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "x-openapi-router-controller": "fakeapi.hello",
            "operationId": "post_greeting",
        },
        app_security=[],
        components=COMPONENTS,
        resolver=Resolver(),
    )
    assert operation.operation_id == "fakeapi.hello.post_greeting"


def test_methodview_resolve_operation_id():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "operationId": "fakeapi.hello.post_greeting",
        },
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.hello.post_greeting"


def test_methodview_resolve_x_router_controller_with_operation_id():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "x-openapi-router-controller": "fakeapi.ExampleMethodView",
            "operationId": "post_greeting",
        },
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.post_greeting"


def test_methodview_resolve_x_router_controller_without_operation_id():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/hello/{id}",
        path_parameters=[],
        operation={"x-openapi-router-controller": "fakeapi.example_method"},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.get"


def test_methodview_resolve_with_default_module_name():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/example_method/{id}",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.get"


def test_methodview_resolve_with_default_module_name_lowercase_verb():
    operation = OpenAPIOperation(
        api=None,
        method="get",
        path="/example_method/{id}",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.get"


def test_methodview_resolve_with_default_module_name_will_translate_dashes_in_resource_name():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/example-method",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.search"


def test_methodview_resolve_with_default_module_name_can_resolve_api_root():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver(
            "fakeapi.example_method",
        ),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.get"


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_get_as_search():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/example_method",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.search"


def test_methodview_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/hello",
        path_parameters=[],
        operation={
            "x-openapi-router-controller": "fakeapi.example_method",
        },
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.search"


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_as_configured():
    operation = OpenAPIOperation(
        api=None,
        method="GET",
        path="/example_method",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi", "api_list"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.api_list"


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_post_as_post():
    operation = OpenAPIOperation(
        api=None,
        method="POST",
        path="/example_method",
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.ExampleMethodView.post"
