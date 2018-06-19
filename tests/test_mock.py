from connexion.mock import MockResolver, partial
from connexion.operation import Swagger2Operation


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

    operation = Swagger2Operation(api=None,
                          method='GET',
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

def test_mock_resolver_ref_schema_example():
    resolver = MockResolver(mock_all=True)

    responses = {
        'default': {
            'schema': {
                '$ref': '#/definitions/Schema'
            }
        }
    }

    operation = Swagger2Operation(api=None,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'responses': responses
                          },
                          app_produces=['application/json'],
                          app_consumes=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={
                              'Schema': {
                                  'example': {
                                      'foo': 'bar'
                                  }
                              }
                          },
                          parameter_definitions={},
                          resolver=resolver)
    assert operation.operation_id == 'mock-1'

    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200
    assert response == {'foo': 'bar'}

def test_mock_resolver_inline_schema_example():
    resolver = MockResolver(mock_all=True)

    responses = {
        'default': {
            'schema': {
                'type': 'object',
                'properties': {
                    'foo': {
                        'type': 'string'
                    }
                },
                'example': {
                    'foo': 'bar'
                }
            }
        }
    }

    operation = Swagger2Operation(api=None,
                          method='GET',
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

    operation = Swagger2Operation(api=None,
                          method='GET',
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

    responses = {
        '418': {}
    }

    # do not mock the existent functions
    operation = Swagger2Operation(api=None,
                          method='GET',
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

    # mock only the nonexistent ones
    operation = Swagger2Operation(api=None,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation={
                              'operationId': 'fakeapi.hello.nonexistent_function',
                              'responses': responses
                          },
                          app_produces=['application/json'],
                          app_consumes=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions={},
                          resolver=resolver)

    # check if it is using the mock function
    assert operation._undecorated_function() == ('No example response was defined.', 418)
