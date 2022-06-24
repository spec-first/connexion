from connexion.operations import OpenAPIOperation
from connexion.resolver import Resolver

COMPONENTS = {'parameters': {'myparam': {'in': 'path', 'schema': {'type': 'integer'}}}}

def test_standard_resolve_x_router_controller():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='endpoint',
        path_parameters=[],
        operation={
            'x-openapi-router-controller': 'fakeapi.hello',
            'operationId': 'post_greeting',
        },
        components=COMPONENTS,
        resolver=Resolver()
    )
    assert operation.operation_id == 'fakeapi.hello.post_greeting'

def test_methodview_resolve_operation_id(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='endpoint',
        path_parameters=[],
        operation={
            'operationId': 'fakeapi.hello.post_greeting',
        },
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.post_greeting'

def test_methodview_resolve_x_router_controller_with_operation_id(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='endpoint',
        path_parameters=[],
        operation={
            'x-openapi-router-controller': 'fakeapi.PetsView',
            'operationId': 'post_greeting',
        },
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.post_greeting'


def test_methodview_resolve_x_router_controller_without_operation_id(method_view_resolver):
    operation = OpenAPIOperation(api=None,
                          method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={'x-openapi-router-controller': 'fakeapi.pets'},
                          components=COMPONENTS,
                          resolver=method_view_resolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.PetsView.get'


def test_methodview_resolve_with_default_module_name(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/pets/{id}',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.get'


def test_methodview_resolve_with_default_module_name_lowercase_verb(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='get',
        path='/pets/{id}',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.get'


def test_methodview_resolve_with_default_module_name_will_translate_dashes_in_resource_name(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/pets',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.search'


def test_methodview_resolve_with_default_module_name_can_resolve_api_root(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi.pets',)
    )
    assert operation.operation_id == 'fakeapi.PetsView.get'


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_get_as_search(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/pets',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.search'


def test_methodview_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/hello',
        path_parameters=[],
        operation={
            'x-openapi-router-controller': 'fakeapi.pets',
        },
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.search'


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_as_configured(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/pets',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi', 'api_list')
    )
    assert operation.operation_id == 'fakeapi.PetsView.api_list'


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_post_as_post(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='POST',
        path='/pets',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.PetsView.post'


def test_method_view_resolver_integration(method_view_app):
    client = method_view_app.app.test_client()

    r = client.get('/v1.0/pets')
    assert r.json == {
        "method": "get"
    }

    r = client.get('/v1.0/pets/1')
    assert r.json == {
        "method": "get",
        "petId": 1
    }

    r = client.post('/v1.0/pets', json={"name": "Musti"})
    assert r.json == {
        "method": "post",
        "body": {
            "name": "Musti"
        }
    }

    r = client.put('/v1.0/pets/1', json={"name": "Igor"})
    assert r.json == {
        "method": "put",
        "petId": 1,
        "body": {
            "name": "Igor"
        }
    }
