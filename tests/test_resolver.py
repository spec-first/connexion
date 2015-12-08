import pytest
import connexion.app
from connexion.resolver import Resolver
from connexion.resolver import RestyResolver
from connexion.operation import Operation

PARAMETER_DEFINITIONS = {'myparam': {'in': 'path', 'type': 'integer'}}


def test_standard_get_function():
    function = Resolver().resolve_function_from_operation_id('connexion.app.App.common_error_handler')
    assert function == connexion.app.App.common_error_handler


def test_resty_get_function():
    function = RestyResolver('connexion').resolve_function_from_operation_id('connexion.app.App.common_error_handler')
    assert function == connexion.app.App.common_error_handler


def test_standard_resolve_x_router_controller():
    operation = Operation(method='GET',
                          path='endpoint',
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
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi', 'list'))
    assert operation.operation_id == 'fakeapi.hello.list'


def test_resty_resolve_with_default_module_name_will_resolve_resource_root_post_as_post():
    operation = Operation(method='POST',
                          path='/hello',
                          operation={},
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=RestyResolver('fakeapi'))
    assert operation.operation_id == 'fakeapi.hello.post'
