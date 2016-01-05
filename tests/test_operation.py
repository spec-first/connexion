from copy import deepcopy
import pathlib
import pytest
import types
from connexion.exceptions import InvalidSpecification
from connexion.operation import Operation
from connexion.decorators.security import security_passthrough, verify_oauth
from connexion.resolver import Resolver

TEST_FOLDER = pathlib.Path(__file__).parent

DEFINITIONS = {'new_stack': {'required': ['image_version', 'keep_stacks', 'new_traffic', 'senza_yaml'],
                             'type': 'object',
                             'properties': {'keep_stacks': {'type': 'integer',
                                                            'description':
                                                                'Number of older stacks to keep'},
                                            'image_version': {'type': 'string',
                                                              'description':
                                                                  'Docker image version to deploy'},
                                            'senza_yaml': {'type': 'string',
                                                           'description': 'YAML to provide to senza'},
                                            'new_traffic': {'type': 'integer',
                                                            'description':
                                                                'Percentage of the traffic'}}},
               'composed': {'required': ['test'],
                            'type': 'object',
                            'properties': {'test': {'schema': {'$ref': '#/definitions/new_stack'}}}}}
PARAMETER_DEFINITIONS = {'myparam': {'in': 'path', 'type': 'integer'}}

OPERATION1 = {'description': 'Adds a new stack to be created by lizzy and returns the '
                             'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'in': 'body',
                              'name': 'new_stack',
                              'required': True,
                              'schema': {'$ref': '#/definitions/new_stack'}}],
              'responses': {201: {'description': 'Stack to be created. The '
                                                 'CloudFormation Stack creation can '
                                                 "still fail if it's rejected by senza "
                                                 'or AWS CF.',
                                  'schema': {'$ref': '#/definitions/stack'}},
                            400: {'description': 'Stack was not created because request '
                                                 'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                                 'access token was not provided or was '
                                                 'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION2 = {'description': 'Adds a new stack to be created by lizzy and returns the '
                             'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'in': 'body',
                              'name': 'new_stack',
                              'required': True,
                              'schema': {'$ref': '#/definitions/new_stack'}},
                             {'in': 'body',
                              'name': 'new_stack',
                              'required': True,
                              'schema': {'$ref': '#/definitions/new_stack'}}],
              'responses': {201: {'description': 'Stack to be created. The '
                                                 'CloudFormation Stack creation can '
                                                 "still fail if it's rejected by senza "
                                                 'or AWS CF.',
                                  'schema': {'$ref': '#/definitions/stack'}},
                            400: {'description': 'Stack was not created because request '
                                                 'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                                 'access token was not provided or was '
                                                 'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION3 = {'description': 'Adds a new stack to be created by lizzy and returns the '
                             'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'in': 'body',
                              'name': 'new_stack',
                              'required': True,
                              'schema': {'$ref': '#/notdefinitions/new_stack'}}],
              'responses': {201: {'description': 'Stack to be created. The '
                                                 'CloudFormation Stack creation can '
                                                 "still fail if it's rejected by senza "
                                                 'or AWS CF.',
                                  'schema': {'$ref': '#/definitions/stack'}},
                            400: {'description': 'Stack was not created because request '
                                                 'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                                 'access token was not provided or was '
                                                 'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION4 = {'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'$ref': '#/parameters/myparam'}]}

OPERATION5 = {'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'$ref': '/parameters/fail'}]}

OPERATION6 = {'description': 'Adds a new stack to be created by lizzy and returns the '
                             'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'in': 'body',
                              'name': 'new_stack',
                              'required': True,
                              'schema': {'type': 'array', 'items': {'$ref': '#/definitions/new_stack'}}}],
              'responses': {201: {'description': 'Stack to be created. The '
                                                 'CloudFormation Stack creation can '
                                                 "still fail if it's rejected by senza "
                                                 'or AWS CF.',
                                  'schema': {'$ref': '#/definitions/stack'}},
                            400: {'description': 'Stack was not created because request '
                                                 'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                                 'access token was not provided or was '
                                                 'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION7 = {'description': 'Adds a new stack to be created by lizzy and returns the '
                             'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'in': 'body',
                              'name': 'test',
                              'required': True,
                              'schema': {'$ref': '#/definitions/composed'}}],
              'responses': {201: {'description': 'Stack to be created. The '
                                                 'CloudFormation Stack creation can '
                                                 "still fail if it's rejected by senza "
                                                 'or AWS CF.',
                                  'schema': {'$ref': '#/definitions/stack'}},
                            400: {'description': 'Stack was not created because request '
                                                 'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                                 'access token was not provided or was '
                                                 'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

SECURITY_DEFINITIONS = {'oauth': {'type': 'oauth2',
                                  'flow': 'password',
                                  'x-tokenInfoUrl': 'https://ouath.example/token_info',
                                  'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_WO_INFO = {'oauth': {'type': 'oauth2',
                                          'flow': 'password',
                                          'scopes': {'myscope': 'can do stuff'}}}


def test_operation():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION1,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions=SECURITY_DEFINITIONS,
                          definitions=DEFINITIONS,
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth as the function and token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects
    assert operation._Operation__security_decorator.func is verify_oauth
    assert operation._Operation__security_decorator.args == ('https://ouath.example/token_info', set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    assert operation.body_schema == DEFINITIONS['new_stack']


def test_operation_array():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION6,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions=SECURITY_DEFINITIONS,
                          definitions=DEFINITIONS,
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth as the function and token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects
    assert operation._Operation__security_decorator.func is verify_oauth
    assert operation._Operation__security_decorator.args == ('https://ouath.example/token_info', set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    assert operation.body_schema == {'type': 'array', 'items': DEFINITIONS['new_stack']}


def test_operation_composed_definition():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION7,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions=SECURITY_DEFINITIONS,
                          definitions=DEFINITIONS,
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth as the function and token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects
    assert operation._Operation__security_decorator.func is verify_oauth
    assert operation._Operation__security_decorator.args == ('https://ouath.example/token_info', set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    definition = deepcopy(DEFINITIONS['composed'])
    definition['properties']['test'] = DEFINITIONS['new_stack']
    assert operation.body_schema == definition


def test_non_existent_reference():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION1,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions={},
                          resolver=Resolver())
    with pytest.raises(InvalidSpecification) as exc_info:  # type: py.code.ExceptionInfo
        schema = operation.body_schema

    exception = exc_info.value
    assert str(exception) == "<InvalidSpecification: GET endpoint Definition 'new_stack' not found>"
    assert repr(exception) == "<InvalidSpecification: GET endpoint Definition 'new_stack' not found>"


def test_multi_body():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION2,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions=DEFINITIONS,
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    with pytest.raises(InvalidSpecification) as exc_info:  # type: py.code.ExceptionInfo
        schema = operation.body_schema

    exception = exc_info.value
    assert str(exception) == "<InvalidSpecification: GET endpoint There can be one 'body' parameter at most>"
    assert repr(exception) == "<InvalidSpecification: GET endpoint There can be one 'body' parameter at most>"


def test_invalid_reference():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION3,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions=DEFINITIONS,
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    with pytest.raises(InvalidSpecification) as exc_info:  # type: py.code.ExceptionInfo
        schema = operation.body_schema

    exception = exc_info.value
    assert str(exception) == "<InvalidSpecification: GET endpoint  '$ref' needs to point to definitions or parameters>"
    assert repr(exception) == "<InvalidSpecification: GET endpoint  '$ref' needs to point to definitions or parameters>"


def test_no_token_info():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION1,
                          app_produces=['application/json'],
                          app_security=SECURITY_DEFINITIONS_WO_INFO,
                          security_definitions=SECURITY_DEFINITIONS_WO_INFO,
                          definitions=DEFINITIONS,
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    assert operation._Operation__security_decorator is security_passthrough

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    assert operation.body_schema == DEFINITIONS['new_stack']


def test_parameter_reference():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION4,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={},
                          definitions={},
                          parameter_definitions=PARAMETER_DEFINITIONS,
                          resolver=Resolver())
    assert operation.parameters == [{'in': 'path', 'type': 'integer'}]


def test_resolve_invalid_reference():
    with pytest.raises(InvalidSpecification) as exc_info:
        Operation(method='GET', path='endpoint', operation=OPERATION5, app_produces=['application/json'],
                  app_security=[], security_definitions={}, definitions={}, parameter_definitions=PARAMETER_DEFINITIONS,
                  resolver=Resolver())

    exception = exc_info.value  # type: InvalidSpecification
    assert exception.reason == "GET endpoint  '$ref' needs to start with '#/'"
