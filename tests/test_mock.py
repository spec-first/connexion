import datetime

from connexion import NoContent
from connexion.mock import MockResolver, partial, sample_from_schema
from connexion.operation import Operation

SCHEMA_DEFINITIONS = {
    'Schema': {
        'type': 'object',
        'properties': {
            'any_int_ro': {
                'type': 'integer',
                'readOnly': True,
            },
            'simple_int_wo': {
                'type': 'integer',
                'example': 42,
                'writeOnly': True,
            },
            'default_float': {
                'type': 'number',
                'format': 'float',
                'default': 42.42
            },
            'min_number': {
                'type': 'number',
                'minimum': 4341,
            },
            'max_number': {
                'type': 'number',
                'maximum': 4443,
            },
            'min_max_float': {
                'type': 'number',
                'format': 'float',
                'minimum': 4541.42,
                'maximum': 4543.42,
            },
            'min_max_integer': {
                'type': 'integer',
                'minimum': 4241,
                'maximum': 4243,
            },
            'simple_string': {
                'type': 'string',
                'example': 'example string'
            },
            'date_string': {
                'type': 'string',
                'format': 'date'
            },
            'datetime_string': {
                'type': 'string',
                'format': 'date-time'
            },
            'simple_array': {
                'type': 'array',
                'items': {'type': 'integer'},
                'example': [42]
            },
            'items_array': {
                'type': 'array',
                'items': {'type': 'string'}
            },
            'implied_array': {
                'items': {'type': 'integer'},
            },
            'implied_object': {
                'properties': {'foo': {'type': 'integer'}},
            },
            'simple_inline_object': {
                'type': 'object',
                'properties': {'foo': {'type': 'string'}},
                'example': {'foo': 'bar'}
            },
            'referenced_object': {
                '$ref': '#/definitions/ReferencedSchema'
            },
            'referenced_array': {
                'type': 'array',
                'items': {
                    '$ref': '#/definitions/ReferencedSchema'
                },
            },
            'simple_enum': {
                'type': 'string',
                'enum': ['foo', 'bar', 'baz'],
            },
            'default_enum': {
                'type': 'string',
                'enum': ['foo', 'bar', 'baz'],
                'default': 'bar',
            },
            'single_enum': {
                'type': 'string',
                'enum': 'baz',
            },
            'additional_object': {
                'type': 'object',
                'additionalProperties': True,
            },
            'additional_integer_object': {
                'type': 'object',
                'additionalProperties': {'type': 'integer'},
            },
            'file': {
                'type': 'file',
            },
        },
    },
    'ReferencedSchema': {
        'type': 'object',
        'properties': {
            'foofoo': {
                'type': 'string',
                'example': 'bazbaz'
            }
        }
    }
}

EXPECTED_RESPONSE = {
    'simple_int_wo': 42,
    'any_int_ro': 0,
    'default_float': 42.42,
    'min_number': 4342,
    'max_number': 4442,
    'min_max_integer': 4242,
    'min_max_float': 4542.42,
    'simple_string': 'example string',
    'date_string': '2017-09-20',  # dynamic, ignored
    'datetime_string': '2017-09-20T21:37:58.345820',  # dynamic, ignored
    'simple_array': [42],
    'implied_array': [0],
    'implied_object': {'foo': 0},
    'items_array': ['string'],
    'simple_inline_object': {'foo': 'bar'},
    'referenced_object': {'foofoo': 'bazbaz'},
    'referenced_array': [{'foofoo': 'bazbaz'}],
    'simple_enum': 'foo',
    'default_enum': 'bar',
    'single_enum': 'baz',
    'additional_object': {'additionalProp1': {}},
    'additional_integer_object': {'additionalProp1': 0, 'additionalProp2': 0, 'additionalProp3': 0},
    'file': None,
}


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

    operation = Operation(api=None,
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

    operation = Operation(api=None,
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

    operation = Operation(api=None,
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


def test_mock_resolver_generated_samples():
    resolver = MockResolver(mock_all=True)

    responses = {
        'default': {
            'schema': {
                '$ref': '#/definitions/Schema'
            }
        }
    }

    operation = Operation(api=None,
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
                          definitions=SCHEMA_DEFINITIONS,
                          parameter_definitions={},
                          resolver=resolver)
    assert operation.operation_id == 'mock-1'

    expected_response = EXPECTED_RESPONSE.copy()
    response, status_code = resolver.mock_operation(operation)
    assert status_code == 200

    # Raises either KeyError if the key is not in the response, or ValueError if the returned format is wrong
    datetime.datetime.strptime(response.pop('date_string'), '%Y-%m-%d')
    datetime.datetime.strptime(response.pop('datetime_string'), '%Y-%m-%dT%H:%M:%S.%f')

    expected_response.pop('date_string')
    expected_response.pop('datetime_string')

    assert response == expected_response


def test_mock_resolver_file():
    resolver = MockResolver(mock_all=True)

    responses = {
        'default': {
            'schema': {
                'type': 'file'
            }
        }
    }

    operation = Operation(api=None,
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
    assert response == 'Cannot generate example response.'


def test_mock_resolver_generated_samples_read_write_only():
    example_ro = sample_from_schema(schema={'$ref': '#/definitions/Schema'}, definitions=SCHEMA_DEFINITIONS,
                                    include_read_only=False)
    example_wo = sample_from_schema(schema={'$ref': '#/definitions/Schema'}, definitions=SCHEMA_DEFINITIONS,
                                    include_write_only=False)

    assert 'any_int_ro' not in example_ro
    assert 'simple_int_wo' not in example_wo


def test_mock_resolver_no_examples():
    resolver = MockResolver(mock_all=True)

    responses = {
        '418': {}
    }

    operation = Operation(api=None,
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
    assert response is NoContent


def test_mock_resolver_notimplemented():
    resolver = MockResolver(mock_all=False)

    responses = {
        '418': {}
    }

    # do not mock the existent functions
    operation = Operation(api=None,
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
    operation = Operation(api=None,
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
    assert operation._Operation__undecorated_function() == (NoContent, 418)
