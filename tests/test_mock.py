
from connexion.mock import MockResolver, partial
from connexion.operation import Operation


def test_partial():
    def func(a, b):
        return a + b

    add_three = partial(func, a=3)
    assert add_three(b=1) == 4


def test_mock_resolver():
    resolver = MockResolver(mock_all=True)

    responses = {
        'default': {
            'examples': {
                'application/json': {
                    'foo': 'bar'
                }
            }
        }
    }

    operation = Operation(method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'responses': responses
                          },
                          app_produces=['application/json'],
                          app_consumes=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions={},
                          resolver=resolver)
    assert operation.operation_id == 'mock-1'

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {'foo': 'bar'}


def test_mock_resolver_no_examples():
    resolver = MockResolver(mock_all=True)

    responses = {
        '418': {}
    }

    operation = Operation(method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'responses': responses
                          },
                          app_produces=['application/json'],
                          app_consumes=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions={},
                          resolver=resolver)
    assert operation.operation_id == 'mock-1'

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 418
    assert response == 'No example response was defined.'


def test_mock_resolver_notimplemented():
    resolver = MockResolver(mock_all=False)

    operation = Operation(method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'operationId': 'fakeapi.hello.get'
                          },
                          app_produces=['application/json'],
                          app_consumes=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions={},
                          resolver=resolver)
    assert operation.operation_id == 'fakeapi.hello.get'
