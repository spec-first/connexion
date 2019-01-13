import copy
import math
import pathlib
import types

import mock
import pytest
from connexion.apis.flask_api import Jsonifier
from connexion.decorators.security import (get_tokeninfo_remote,
                                           validate_scope, verify_security)
from connexion.exceptions import InvalidSpecification
from connexion.json_schema import resolve_refs
from connexion.operations import Swagger2Operation
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
                            'properties': {'test': {'schema': {'$ref': '#/definitions/new_stack'}}}},
               'problem': {"not": "defined"}}
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
                                  'schema': {'$ref': '#/definitions/new_stack'}},
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
                                  'schema': {'$ref': '#/definitions/new_stack'}},
                            400: {'description': 'Stack was not created because request '
                                  'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                  'access token was not provided or was '
                                  'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION3 = {'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'$ref': '#/parameters/myparam'}]}

OPERATION4 = {'description': 'Adds a new stack to be created by lizzy and returns the '
              'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [
                  {
                      'in': 'body',
                      'name': 'new_stack',
                      'required': True,
                      'schema': {'$ref': '#/definitions/new_stack'}
                  },
                  {
                      'in': 'query',
                      'name': 'stack_version',
                      'default': 'one',
                      'type': 'number'
                  }
              ],
              'responses': {201: {'description': 'Stack to be created. The '
                                  'CloudFormation Stack creation can '
                                  "still fail if it's rejected by senza "
                                  'or AWS CF.',
                                  'schema': {'$ref': '#/definitions/new_stack'}},
                            400: {'description': 'Stack was not created because request '
                                  'was invalid',
                                  'schema': {'$ref': '#/definitions/problem'}},
                            401: {'description': 'Stack was not created because the '
                                  'access token was not provided or was '
                                  'not valid for this operation',
                                  'schema': {'$ref': '#/definitions/problem'}}},
              'summary': 'Create new stack'}

OPERATION5 = {
    'description': 'Adds a new stack to be created by lizzy and returns the '
    'information needed to keep track of deployment',
    'operationId': 'fakeapi.hello.post_greeting',
    'parameters': [
        {
            'in': 'body',
            'name': 'new_stack',
            'required': True,
            'type': 'integer',
            'default': 'stack'
        }
    ],
    'responses': {'201': {'description': 'Stack to be created. The '
                          'CloudFormation Stack creation can '
                          "still fail if it's rejected by senza "
                          'or AWS CF.',
                          'schema': {'$ref': '#/definitions/new_stack'}},
                  '400': {'description': 'Stack was not created because request '
                          'was invalid',
                          'schema': {'$ref': '#/definitions/problem'}},
                  '401': {'description': 'Stack was not created because the '
                          'access token was not provided or was '
                          'not valid for this operation',
                          'schema': {'$ref': '#/definitions/problem'}}},
    'security': [{'oauth': ['uid']}],
    'summary': 'Create new stack'
}

OPERATION6 = {
    'operationId': 'fakeapi.hello.schema',
    'parameters': [
        {
            'type': 'object',
            'in': 'body',
            'name': 'new_stack',
            'default': {'keep_stack': 1, 'image_version': 1, 'senza_yaml': 'senza.yaml',
                        'new_traffic': 100},
            'schema': {'$ref': '#/definitions/new_stack'}
        }
    ],
    'responses': {},
    'security': [{'oauth': ['uid']}],
    'summary': 'Create new stack'
}

OPERATION7 = {'description': 'Adds a new stack to be created by lizzy and returns the '
              'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'in': 'body',
                              'name': 'new_stack',
                              'required': True,
                              'schema': {'type': 'array', 'items': {'$ref': '#/definitions/new_stack'}}}],
              'responses': {'201': {'description': 'Stack to be created. The '
                                    'CloudFormation Stack creation can '
                                    "still fail if it's rejected by senza "
                                    'or AWS CF.',
                                    'schema': {'$ref': '#/definitions/new_stack'}},
                            '400': {'description': 'Stack was not created because request '
                                    'was invalid',
                                    'schema': {'$ref': '#/definitions/problem'}},
                            '401': {'description': 'Stack was not created because the '
                                    'access token was not provided or was '
                                    'not valid for this operation',
                                    'schema': {'$ref': '#/definitions/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION8 = {'description': 'Adds a new stack to be created by lizzy and returns the '
               'information needed to keep track of deployment',
               'operationId': 'fakeapi.hello.post_greeting',
               'parameters': [{'in': 'body',
                               'name': 'test',
                               'required': True,
                               'schema': {'$ref': '#/definitions/composed'}}],
               'responses': {'201': {'description': 'Stack to be created. The '
                                     'CloudFormation Stack creation can '
                                     "still fail if it's rejected by senza "
                                     'or AWS CF.',
                                     'schema': {'$ref': '#/definitions/new_stack'}},
                             '400': {'description': 'Stack was not created because request '
                                     'was invalid',
                                     'schema': {'$ref': '#/definitions/problem'}},
                             '401': {'description': 'Stack was not created because the '
                                     'access token was not provided or was '
                                     'not valid for this operation',
                                     'schema': {'$ref': '#/definitions/problem'}}},
               'security': [{'oauth': ['uid']}],
               'summary': 'Create new stack'}

SECURITY_DEFINITIONS_REMOTE = {'oauth': {'type': 'oauth2',
                                         'flow': 'password',
                                         'x-tokenInfoUrl': 'https://oauth.example/token_info',
                                         'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_LOCAL = {'oauth': {'type': 'oauth2',
                                        'flow': 'password',
                                        'x-tokenInfoFunc': 'math.ceil',
                                        'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_BOTH = {'oauth': {'type': 'oauth2',
                                       'flow': 'password',
                                       'x-tokenInfoFunc': 'math.ceil',
                                       'x-tokenInfoUrl': 'https://oauth.example/token_info',
                                       'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_WO_INFO = {'oauth': {'type': 'oauth2',
                                          'flow': 'password',
                                          'scopes': {'myscope': 'can do stuff'}}}


@pytest.fixture
def api():
  return mock.MagicMock(jsonifier=Jsonifier)


def make_operation(op, definitions=True, parameters=True):
    """ note the wrapper because definitions namespace and
        operation namespace collide
    """
    new_op = {"wrapper": copy.deepcopy(op)}
    if definitions:
        new_op.update({"definitions": DEFINITIONS})
    if parameters:
        new_op.update({"parameters": PARAMETER_DEFINITIONS})
    return resolve_refs(new_op)["wrapper"]


def test_operation(api, monkeypatch):
    dummy = object()
    verify_oauth = mock.MagicMock(return_value=dummy)
    monkeypatch.setattr('connexion.operations.secure.verify_oauth', verify_oauth)

    op_spec = make_operation(OPERATION1)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=[],
                                  security_definitions=SECURITY_DEFINITIONS_REMOTE,
                                  definitions=DEFINITIONS,
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    security_decorator = operation.security_decorator
    assert security_decorator.func is verify_security
    assert len(security_decorator.args[0]) == 1
    assert security_decorator.args[0][0] is dummy
    assert security_decorator.args[1] == ['uid']
    call_args = verify_oauth.call_args[0]
    assert call_args[0].func is get_tokeninfo_remote
    assert call_args[0].args == ('https://oauth.example/token_info',)
    assert call_args[1] is validate_scope

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]

    expected_body_schema = op_spec["parameters"][0]["schema"]
    expected_body_schema.update({'definitions': DEFINITIONS})
    assert operation.body_schema == expected_body_schema


def test_operation_array(api):
    op_spec = make_operation(OPERATION7)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=[],
                                  security_definitions=SECURITY_DEFINITIONS_REMOTE,
                                  definitions=DEFINITIONS,
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = {
        'type': 'array',
        'items': DEFINITIONS["new_stack"],
        'definitions': DEFINITIONS
    }
    assert operation.body_schema == expected_body_schema


def test_operation_composed_definition(api):
    op_spec = make_operation(OPERATION8)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=[],
                                  security_definitions=SECURITY_DEFINITIONS_REMOTE,
                                  definitions=DEFINITIONS,
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = op_spec["parameters"][0]["schema"]
    expected_body_schema.update({'definitions': DEFINITIONS})
    assert operation.body_schema == expected_body_schema


def test_operation_local_security_oauth2(api, monkeypatch):
    dummy = object()
    verify_oauth = mock.MagicMock(return_value=dummy)
    monkeypatch.setattr('connexion.operations.secure.verify_oauth', verify_oauth)

    op_spec = make_operation(OPERATION8)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=[],
                                  security_definitions=SECURITY_DEFINITIONS_LOCAL,
                                  definitions=DEFINITIONS,
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    security_decorator = operation.security_decorator
    assert security_decorator.func is verify_security
    assert len(security_decorator.args[0]) == 1
    assert security_decorator.args[0][0] is dummy
    assert security_decorator.args[1] == ['uid']
    call_args = verify_oauth.call_args[0]
    assert call_args[0] is math.ceil
    assert call_args[1] is validate_scope

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = op_spec["parameters"][0]["schema"]
    expected_body_schema.update({'definitions': DEFINITIONS})
    assert operation.body_schema == expected_body_schema


def test_operation_local_security_duplicate_token_info(api, monkeypatch):
    dummy = object()
    verify_oauth = mock.MagicMock(return_value=dummy)
    monkeypatch.setattr('connexion.operations.secure.verify_oauth', verify_oauth)

    op_spec = make_operation(OPERATION8)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=[],
                                  security_definitions=SECURITY_DEFINITIONS_BOTH,
                                  definitions=DEFINITIONS,
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    security_decorator = operation.security_decorator
    assert security_decorator.func is verify_security
    assert len(security_decorator.args[0]) == 1
    assert security_decorator.args[0][0] is dummy
    assert security_decorator.args[1] == ['uid']
    call_args = verify_oauth.call_args[0]
    assert call_args[0] is math.ceil
    assert call_args[1] is validate_scope

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = op_spec["parameters"][0]["schema"]
    expected_body_schema.update({'definitions': DEFINITIONS})
    assert operation.body_schema == expected_body_schema


def test_multi_body(api):
    with pytest.raises(InvalidSpecification) as exc_info:  # type: py.code.ExceptionInfo
        op_spec = make_operation(OPERATION2)
        operation = Swagger2Operation(api=api,
                                      method='GET',
                                      path='endpoint',
                                      path_parameters=[],
                                      operation=op_spec,
                                      app_produces=['application/json'],
                                      app_consumes=['application/json'],
                                      app_security=[],
                                      security_definitions={},
                                      definitions=DEFINITIONS,
                                      parameter_definitions=PARAMETER_DEFINITIONS,
                                      resolver=Resolver())
        operation.body_schema

    exception = exc_info.value
    assert str(exception) == "GET endpoint There can be one 'body' parameter at most"
    assert repr(exception) == """<InvalidSpecification: "GET endpoint There can be one 'body' parameter at most">"""


def test_no_token_info(api):
    op_spec = make_operation(OPERATION1)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=SECURITY_DEFINITIONS_WO_INFO,
                                  security_definitions=SECURITY_DEFINITIONS_WO_INFO,
                                  definitions=DEFINITIONS,
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    security_decorator = operation.security_decorator
    assert security_decorator.func is verify_security
    assert len(security_decorator.args[0]) == 0

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]

    expected_body_schema = {'definitions': DEFINITIONS}
    expected_body_schema.update(DEFINITIONS["new_stack"])
    assert operation.body_schema == expected_body_schema


def test_parameter_reference(api):
    op_spec = make_operation(OPERATION3, definitions=False)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  app_security=[],
                                  security_definitions={},
                                  definitions={},
                                  parameter_definitions=PARAMETER_DEFINITIONS,
                                  resolver=Resolver())
    assert operation.parameters == [{'in': 'path', 'type': 'integer'}]


def test_default(api):
    op_spec = make_operation(OPERATION4)
    op_spec['parameters'][1]['default'] = 1
    Swagger2Operation(
        api=api, method='GET', path='endpoint', path_parameters=[],
        operation=op_spec, app_produces=['application/json'],
        app_consumes=['application/json'], app_security=[],
        security_definitions={}, definitions=DEFINITIONS,
        parameter_definitions=PARAMETER_DEFINITIONS, resolver=Resolver()
    )
    op_spec = make_operation(OPERATION6, parameters=False)
    op_spec['parameters'][0]['default'] = {
        'keep_stacks': 1,
        'image_version': 'one',
        'senza_yaml': 'senza.yaml',
        'new_traffic': 100
    }
    Swagger2Operation(
        api=api, method='POST', path='endpoint', path_parameters=[],
        operation=op_spec, app_produces=['application/json'],
        app_consumes=['application/json'], app_security=[],
        security_definitions={}, definitions=DEFINITIONS,
        parameter_definitions={}, resolver=Resolver()
    )


def test_get_path_parameter_types(api):
    op_spec = make_operation(OPERATION1, parameters=False)
    op_spec['parameters'] = [
        {'in': 'path', 'type': 'int', 'name': 'int_path'},
        {'in': 'path', 'type': 'string', 'name': 'string_path'},
        {'in': 'path', 'type': 'string', 'format': 'path', 'name': 'path_path'}
    ]

    operation = Swagger2Operation(
        api=api, method='GET', path='endpoint', path_parameters=[],
        operation=op_spec, app_produces=['application/json'],
        app_consumes=['application/json'],
        definitions=DEFINITIONS, resolver=Resolver()
    )

    assert {'int_path': 'int', 'string_path': 'string', 'path_path': 'path'} == operation.get_path_parameter_types()
