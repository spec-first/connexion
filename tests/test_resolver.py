import connexion.app
from connexion.exceptions import ResolverError
from connexion.operation import Operation
from connexion.resolver import Resolver, RestyResolver

import pytest

PARAMETER_DEFINITIONS = {'myparam': {'in': 'path', 'type': 'integer'}}


def test_standard_get_function():
    function = Resolver().resolve_function_from_operation_id('connexion.app.App.common_error_handler')
    assert function == connexion.app.App.common_error_handler


def test_resty_get_function():
    function = RestyResolver('connexion').resolve_function_from_operation_id('connexion.app.App.common_error_handler')
    assert function == connexion.app.App.common_error_handler


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
    operation = Operation(method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'x-swagger-router-controller': 'fakeapi.hello',
                              'operationId': 'post_greeting',
                          },
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_operation_id():
    operation = Operation(method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'operationId': 'fakeapi.hello.post_greeting',
                          },
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_x_router_controller_with_operation_id():
    operation = Operation(method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'x-swagger-router-controller': 'fakeapi.hello',
                              'operationId': 'post_greeting',
                          },
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post_greeting'


def test_resty_resolve_x_router_controller_without_operation_id():
    operation = Operation(method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={'x-swagger-router-controller': 'fakeapi.hello'},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name():
    operation = Operation(method='GET',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name_lowercase_verb():
    operation = Operation(method='get',
                          path='/hello/{id}',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.get'


def test_resty_resolve_with_default_module_name_will_translate_dashes_in_resource_name():
    operation = Operation(method='GET',
                          path='/foo-bar',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.foo_bar.search'


def test_resty_resolve_with_default_module_name_can_resolve_api_root():
    operation = Operation(method='GET',
                          path='/',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.get'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_get_as_search():
    operation = Operation(method='GET',
                          path='/hello',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.search'


def test_resty_resolve_with_default_module_name_and_x_router_controller_will_resolve_resource_root_get_as_search():
    operation = Operation(method='GET',
                          path='/hello',
                          path_parameters=[],
                          operation={
                              'x-swagger-router-controller': 'fakeapi.hello',
                          },
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.search'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_as_configured():
    operation = Operation(method='GET',
                          path='/hello',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi', 'api_list'))
    assert operation.operation_id == 'fakeapi.hello.api_list'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_post_as_post():
    operation = Operation(method='POST',
                          path='/hello',
                          path_parameters=[],
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post'
