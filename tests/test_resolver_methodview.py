from connexion import FlaskApp
from connexion.operations import OpenAPIOperation
from connexion.resolver import MethodResolver, MethodViewResolver, Resolver

from conftest import build_app_from_fixture

COMPONENTS = {"parameters": {"myparam": {"in": "path", "schema": {"type": "integer"}}}}


def test_standard_resolve_x_router_controller():
    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "x-openapi-router-controller": "fakeapi.hello",
            "operationId": "post_greeting",
        },
        components=COMPONENTS,
        resolver=Resolver(),
    )
    assert operation.operation_id == "fakeapi.hello.post_greeting"


def test_methodview_resolve_operation_id(method_view_resolver):
    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "operationId": "fakeapi.hello.post_greeting",
        },
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.hello.post_greeting"


def test_methodview_resolve_x_router_controller_with_operation_id(method_view_resolver):
    operation = OpenAPIOperation(
        method="GET",
        path="endpoint",
        path_parameters=[],
        operation={
            "x-openapi-router-controller": "fakeapi.PetsView",
            "operationId": "post_greeting",
        },
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.post_greeting"


def test_methodview_resolve_x_router_controller_without_operation_id(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="GET",
        path="/hello/{id}",
        path_parameters=[],
        operation={"x-openapi-router-controller": "fakeapi.pets"},
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.get"


def test_methodview_resolve_with_default_module_name(method_view_resolver):
    operation = OpenAPIOperation(
        method="GET",
        path="/pets/{id}",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.get"


def test_methodview_resolve_with_default_module_name_lowercase_verb(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="get",
        path="/pets/{id}",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.get"


def test_methodview_resolve_with_default_module_name_will_translate_dashes_in_resource_name(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="GET",
        path="/pets",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.search"


def test_methodview_resolve_with_default_module_name_can_resolve_api_root(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="GET",
        path="/",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver(
            "fakeapi.pets",
        ),
    )
    assert operation.operation_id == "fakeapi.PetsView.get"


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_get_as_search(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="GET",
        path="/pets",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.search"


def test_methodview_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="GET",
        path="/hello",
        path_parameters=[],
        operation={
            "x-openapi-router-controller": "fakeapi.pets",
        },
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.search"


def test_method_resolve_with_default_module_name_will_resolve_resource_root_as_configured():
    operation = OpenAPIOperation(
        method="GET",
        path="/pets",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=MethodResolver("fakeapi", collection_endpoint_name="api_list"),
    )
    assert operation.operation_id == "fakeapi.PetsView.api_list"


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_as_configured():
    operation = OpenAPIOperation(
        method="GET",
        path="/pets",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=MethodViewResolver("fakeapi", collection_endpoint_name="api_list"),
    )
    # The collection_endpoint_name is ignored
    assert operation.operation_id == "fakeapi.PetsView.search"


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_post_as_post(
    method_view_resolver,
):
    operation = OpenAPIOperation(
        method="POST",
        path="/pets",
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver("fakeapi"),
    )
    assert operation.operation_id == "fakeapi.PetsView.post"


def test_method_view_resolver_integration(spec):
    method_view_app = build_app_from_fixture(
        "method_view",
        app_class=FlaskApp,
        spec_file=spec,
        resolver=MethodViewResolver("fakeapi.example_method_view"),
    )

    client = method_view_app.test_client()

    r = client.get("/v1.0/pets")
    assert r.json() == [{"name": "get"}]

    r = client.get("/v1.0/pets/1")
    assert r.json() == {"name": "get", "petId": 1}

    r = client.post("/v1.0/pets", json={"name": "Musti"})
    assert r.json() == {"name": "post", "body": {"name": "Musti"}}

    r = client.put("/v1.0/pets/1", json={"name": "Igor"})
    assert r.json() == {"name": "put", "petId": 1, "body": {"name": "Igor"}}


def test_method_resolver_integration(spec, app_class):
    method_view_app = build_app_from_fixture(
        "method_view",
        app_class=app_class,
        spec_file=spec,
        resolver=MethodResolver("fakeapi.example_method_class"),
    )

    client = method_view_app.test_client()

    r = client.get("/v1.0/pets")
    assert r.json() == [{"name": "search"}]

    r = client.get("/v1.0/pets/1")
    assert r.json() == {"name": "get", "petId": 1}

    r = client.post("/v1.0/pets", json={"name": "Musti"})
    assert r.json() == {"name": "post", "body": {"name": "Musti"}}

    r = client.put("/v1.0/pets/1", json={"name": "Igor"})
    assert r.json() == {"name": "put", "petId": 1, "body": {"name": "Igor"}}
