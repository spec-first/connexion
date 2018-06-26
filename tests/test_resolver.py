import connexion.apps
import pytest
from connexion.exceptions import ResolverError
from connexion.operation import Operation, Swagger2Operation
from connexion.resolver import Resolver, RestyResolver

COMPONENTS = {'parameters': {'myparam': {'in': 'path', 'schema': {'type': 'integer'}}}}


def test_standard_get_function():
    function = Resolver().resolve_function_from_operation_id('connexion.FlaskApp.common_error_handler')
    assert function == connexion.FlaskApp.common_error_handler


def test_resty_get_function():
    function = RestyResolver('connexion').resolve_function_from_operation_id('connexion.FlaskApp.common_error_handler')
    assert function == connexion.FlaskApp.common_error_handler


def test_missing_operation_id():
    # Missing operationIDs should result in a well-defined error that can
    # be handled upstream.
    with pytest.raises(ResolverError):
        Resolver().resolve_function_from_operation_id(None)
    with pytest.raises(ResolverError):
        RestyResolver('connexion').resolve_function_from_operation_id(None)


def test_bad_operation_id():
    # Unresolvable operationIDs should result in a well-defined error that can
    # be handled upstream.
    with pytest.raises(ResolverError):
        Resolver().resolve_function_from_operation_id('ohai.I.do.not.exist')
    with pytest.raises(ResolverError):
        RestyResolver('connexion').resolve_function_from_operation_id('ohai.I.do.not.exist')


def test_standard_resolve_x_router_controller():
    operation = Operation(api=None,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'x-swagger-router-controller': 'fakeapi.hello',
                              'operationId': 'post_greeting',
                          },
                          app_security=[],
                          components=COMPONENTS,
                          resolver=Resolver())
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_operation_id():
    operation = Operation(api=None,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'operationId': 'fakeapi.hello.post_greeting',
                          },
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_x_router_controller_with_operation_id():
    operation = Operation(api=None,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'x-swagger-router-controller': 'fakeapi.hello',
                              'operationId': 'post_greeting',
                          },
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_x_router_controller_without_operation_id():
    operation = Operation(api=None,
                          method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={'x-swagger-router-controller': 'fakeapi.hello'},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name():
    operation = Operation(api=None,
                          method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name_lowercase_verb():
    operation = Operation(api=None,
                          method='get',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name_will_translate_dashes_in_resource_name():
    operation = Operation(api=None,
                          method='GET',
                          path='/foo-bar',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.foo_bar.search'


def test_resty_resolve_with_default_module_name_can_resolve_api_root():
    operation = Operation(api=None,
                          method='GET',
                          path='/',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.get'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_get_as_search():
    operation = Operation(api=None,
                          method='GET',
                          path='/hello',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.search'


def test_resty_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search():
    operation = Operation(api=None,
                          method='GET',
                          path='/hello',
                          path_parameters=[],
                          operation={
                              'x-swagger-router-controller': 'fakeapi.hello',
                          },
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.search'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_as_configured():
    operation = Operation(api=None,
                          method='GET',
                          path='/hello',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi', 'api_list'))
    assert operation.operation_id == 'fakeapi.hello.api_list'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_post_as_post():
    operation = Operation(api=None,
                          method='POST',
                          path='/hello',
                          path_parameters=[],
                          operation={},
                          app_security=[],
                          components=COMPONENTS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post'
