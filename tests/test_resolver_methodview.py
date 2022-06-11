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
            'x-openapi-router-controller': 'fakeapi.ExampleMethodView',
            'operationId': 'post_greeting',
        },
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.post_greeting'


def test_methodview_resolve_x_router_controller_without_operation_id(method_view_resolver):
    operation = OpenAPIOperation(api=None,
                          method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={'x-openapi-router-controller': 'fakeapi.example_method'},
                          components=COMPONENTS,
                          resolver=method_view_resolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.ExampleMethodView.get'


def test_methodview_resolve_with_default_module_name(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/example_method/{id}',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.get'


def test_methodview_resolve_with_default_module_name_lowercase_verb(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='get',
        path='/example_method/{id}',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.get'


def test_methodview_resolve_with_default_module_name_will_translate_dashes_in_resource_name(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/example-method',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.search'


def test_methodview_resolve_with_default_module_name_can_resolve_api_root(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi.example_method',)
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.get'


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_get_as_search(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/example_method',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.search'


def test_methodview_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/hello',
        path_parameters=[],
        operation={
            'x-openapi-router-controller': 'fakeapi.example_method',
        },
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.search'


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_as_configured(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='GET',
        path='/example_method',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi', 'api_list')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.api_list'


def test_methodview_resolve_with_default_module_name_will_resolve_resource_root_post_as_post(method_view_resolver):
    operation = OpenAPIOperation(
        api=None,
        method='POST',
        path='/example_method',
        path_parameters=[],
        operation={},
        components=COMPONENTS,
        resolver=method_view_resolver('fakeapi')
    )
    assert operation.operation_id == 'fakeapi.ExampleMethodView.post'
