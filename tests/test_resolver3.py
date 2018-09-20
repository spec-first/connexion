from connexion.operations import OpenAPIOperation
from connexion.resolver import Resolver, RestyResolver

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
        app_security=[],
        components=COMPONENTS,
        resolver=Resolver()
    )
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_operation_id():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='endpoint',
        path_parameters=[],
        operation={
            'operationId': 'fakeapi.hello.post_greeting',
        },
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_x_router_controller_with_operation_id():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='endpoint',
        path_parameters=[],
        operation={
            'x-openapi-router-controller': 'fakeapi.hello',
            'operationId': 'post_greeting',
        },
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_x_router_controller_without_operation_id():
    operation = OpenAPIOperation(api=None,
                          method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={'x-openapi-router-controller': 'fakeapi.hello'},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/hello/{id}',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name_lowercase_verb():
    operation = OpenAPIOperation(
        api=None,
        method='get',
        path='/hello/{id}',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name_will_translate_dashes_in_resource_name():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/foo-bar',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.foo_bar.search'


def test_resty_resolve_with_default_module_name_can_resolve_api_root():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.get'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_get_as_search():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/hello',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.search'


def test_resty_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/hello',
        path_parameters=[],
        operation={
            'x-openapi-router-controller': 'fakeapi.hello',
        },
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.search'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_as_configured():
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/hello',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi', 'api_list')
    )
    assert operation.operation_id == 'fakeapi.hello.api_list'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_post_as_post():
    operation = OpenAPIOperation(
        api=None,
        method='POST',
        path='/hello',
        path_parameters=[],
        operation={},
        app_security=[],
        components=COMPONENTS,
        resolver=RestyResolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.hello.post'
