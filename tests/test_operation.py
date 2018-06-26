import math
import pathlib
import types
from copy import deepcopy

import mock
import pytest
from connexion.apis.flask_api import Jsonifier
from connexion.decorators.security import (security_passthrough,
                                           verify_oauth_local,
                                           verify_oauth_remote)
from connexion.exceptions import InvalidSpecification
from connexion.operations import OpenAPIOperation
from connexion.resolver import Resolver

TEST_FOLDER = pathlib.Path(__file__).parent


COMPONENTS = {
    "schemas": {
        'new_stack': {
                'required': ['image_version', 'keep_stacks', 'new_traffic', 'senza_yaml'],
                'type': 'object',
                'properties': {
                    'keep_stacks': {
                        'type': 'integer',
                        'description': 'Number of older stacks to keep'
                    },
                    'image_version': {
                        'type': 'string',
                        'description': 'Docker image version to deploy'
                    },
                    'senza_yaml': {
                        'type': 'string',
                        'description': 'YAML to provide to senza'
                    },
                    'new_traffic': {
                        'type': 'integer',
                        'description': 'Percentage of the traffic'
                    }
                }
        },
        'problem': {'type': 'object'},
        'composed': {
                'required': ['test'],
                'type': 'object',
                'properties': {
                    'test': {
                            '$ref': '#/components/schemas/new_stack'
                    }
                }
        }
    },
    'parameters': {
        'myparam': {'in': 'path', 'schema': {'type': 'integer'}}
    }
}

OPERATION1 = {'description': 'Adds a new stack to be created by lizzy and returns the '
              'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'requestBody': {'content': {'application/json': {
                              'schema': {'$ref': '#/components/schemas/new_stack'}}}},
              'responses': {201: {'description': 'Stack to be created. The '
                                  'CloudFormation Stack creation can '
                                  "still fail if it's rejected by senza "
                                  'or AWS CF.',
                                  'schema': {'$ref': '#/components/schemas/new_stack'}},
                            400: {'description': 'Stack was not created because request '
                                  'was invalid',
                                  'schema': {'$ref': '#/components/schemas/problem'}},
                            401: {'description': 'Stack was not created because the '
                                  'access token was not provided or was '
                                  'not valid for this operation',
                                  'schema': {'$ref': '#/components/schemas/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION3 = {'description': 'Adds a new stack to be created by lizzy and returns the '
              'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'requestBody': {'content': {'application/json': {
                              'schema': {'$ref': '#/notcomponents/schemas/new_stack'}}}},
              'responses': {201: {'description': 'Stack to be created. The '
                                  'CloudFormation Stack creation can '
                                  "still fail if it's rejected by senza "
                                  'or AWS CF.',
                                  'schema': {'$ref': '#/components/schemas/new_stack'}},
                            400: {'description': 'Stack was not created because request '
                                  'was invalid',
                                  'schema': {'$ref': '#/components/schemas/problem'}},
                            401: {'description': 'Stack was not created because the '
                                  'access token was not provided or was '
                                  'not valid for this operation',
                                  'schema': {'$ref': '#/components/schemas/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION4 = {'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'$ref': '#/components/parameters/myparam'}]}

OPERATION5 = {'operationId': 'fakeapi.hello.post_greeting',
              'parameters': [{'$ref': '/components/parameters/fail'}]}

OPERATION6 = {'description': 'Adds a new stack to be created by lizzy and returns the '
              'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'requestBody': {'content': {'application/json': {
                              'schema': {'$ref': '#/components/schemas/new_stack'}}}},
              'parameters': [
                  {
                      'in': 'query',
                      'name': 'stack_version',
                      'default': 'one',
                      'schema': {
                          'type': 'number'
                      }
                  }
              ],
              'responses': {201: {'description': 'Stack to be created. The '
                                  'CloudFormation Stack creation can '
                                  "still fail if it's rejected by senza "
                                  'or AWS CF.',
                                  'schema': {'$ref': '#/components/schemas/new_stack'}},
                            400: {'description': 'Stack was not created because request '
                                  'was invalid',
                                  'schema': {'$ref': '#/components/schemas/problem'}},
                            401: {'description': 'Stack was not created because the '
                                  'access token was not provided or was '
                                  'not valid for this operation',
                                  'schema': {'$ref': '#/components/schemas/problem'}}},
              'summary': 'Create new stack'}

OPERATION7 = {
    'description': 'Adds a new stack to be created by lizzy and returns the '
    'information needed to keep track of deployment',
    'operationId': 'fakeapi.hello.post_greeting',
    'requestBody': {'content': {'application/json': {
                    'schema': {'$ref': '#/components/schemas/new_stack'},
                    'default': 'stack'}}},
    'responses': {'201': {'description': 'Stack to be created. The '
                          'CloudFormation Stack creation can '
                          "still fail if it's rejected by senza "
                          'or AWS CF.',
                          'schema': {'$ref': '#/components/schemas/new_stack'}},
                  '400': {'description': 'Stack was not created because request '
                          'was invalid',
                          'schema': {'$ref': '#/components/schemas/problem'}},
                  '401': {'description': 'Stack was not created because the '
                          'access token was not provided or was '
                          'not valid for this operation',
                          'schema': {'$ref': '#/components/schemas/problem'}}},
    'security': [{'oauth': ['uid']}],
    'summary': 'Create new stack'
}

OPERATION8 = {
    'operationId': 'fakeapi.hello.schema',
    'requestBody': {'content': {'application/json': {
                    'schema': {'$ref': '#/components/schemas/new_stack'},
                    'default': {'keep_stack': 1, 'image_version': 1, 'senza_yaml': 'senza.yaml',
                                'new_traffic': 100}}}},
    'responses': {},
    'security': [{'oauth': ['uid']}],
    'summary': 'Create new stack'
}

OPERATION9 = {'description': 'Adds a new stack to be created by lizzy and returns the '
              'information needed to keep track of deployment',
              'operationId': 'fakeapi.hello.post_greeting',
              'requestBody': {'content': {'application/json': {
                              'schema': {'type': 'array',
                                         'items': {'$ref': '#/components/schemas/new_stack'}}}}},
              'responses': {'201': {'description': 'Stack to be created. The '
                                    'CloudFormation Stack creation can '
                                    "still fail if it's rejected by senza "
                                    'or AWS CF.',
                                    'schema': {'$ref': '#/components/schemas/new_stack'}},
                            '400': {'description': 'Stack was not created because request '
                                    'was invalid',
                                    'schema': {'$ref': '#/components/schemas/problem'}},
                            '401': {'description': 'Stack was not created because the '
                                    'access token was not provided or was '
                                    'not valid for this operation',
                                    'schema': {'$ref': '#/components/schemas/problem'}}},
              'security': [{'oauth': ['uid']}],
              'summary': 'Create new stack'}

OPERATION10 = {'description': 'Adds a new stack to be created by lizzy and returns the '
               'information needed to keep track of deployment',
               'operationId': 'fakeapi.hello.post_greeting',
               'requestBody': {'content': {'application/json': {
                              'schema': {'$ref': '#/components/schemas/composed'}}}},
               'responses': {'201': {'description': 'Stack to be created. The '
                                     'CloudFormation Stack creation can '
                                     "still fail if it's rejected by senza "
                                     'or AWS CF.',
                                     'schema': {'$ref': '#/components/schemas/new_stack'}},
                             '400': {'description': 'Stack was not created because request '
                                     'was invalid',
                                     'schema': {'$ref': '#/components/schemas/problem'}},
                             '401': {'description': 'Stack was not created because the '
                                     'access token was not provided or was '
                                     'not valid for this operation',
                                     'schema': {'$ref': '#/components/schemas/problem'}}},
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


def test_operation(api):
    components = deepcopy(COMPONENTS)
    components.update({"securitySchemes": SECURITY_DEFINITIONS_REMOTE})
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION1,
                          app_security=[],
                          components=components,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth_remote as the function and token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects
    assert operation.security_decorator.func is verify_oauth_remote
    assert operation.security_decorator.args == ('https://oauth.example/token_info', set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]

    expected_body_schema = {"components": components}
    expected_body_schema.update(components["schemas"]["new_stack"])
    assert operation.body_schema == expected_body_schema


def test_operation_array(api):
    components = deepcopy(COMPONENTS)
    components.update({"securitySchemes": SECURITY_DEFINITIONS_REMOTE})
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION9,
                          app_security=[],
                          components=components,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth_remote as the function and token url
    #  and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects
    assert operation.security_decorator.func is verify_oauth_remote
    assert operation.security_decorator.args == ('https://oauth.example/token_info', set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]

    expected_body_schema = {}
    expected_body_schema.update({
        'type': 'array',
        'items': components["schemas"]["new_stack"]
    })
    assert operation.body_schema == expected_body_schema


def test_operation_composed_definition(api):
    components = deepcopy(COMPONENTS)
    components.update({"securitySchemes": SECURITY_DEFINITIONS_REMOTE})
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION10,
                          app_security=[],
                          components=components,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth_remote as the function and
    # token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects
    assert operation.security_decorator.func is verify_oauth_remote
    assert operation.security_decorator.args == ('https://oauth.example/token_info', set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = {"components": components}
    expected_body_schema.update(components["schemas"]["composed"])
    assert operation.body_schema == expected_body_schema


def test_operation_local_security_oauth2(api):
    components = deepcopy(COMPONENTS)
    components.update({"securitySchemes": SECURITY_DEFINITIONS_LOCAL})
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION10,
                          app_security=[],
                          components=components,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth_remote as the function and
    # token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects

    assert operation.security_decorator.func is verify_oauth_local
    assert operation.security_decorator.args == (math.ceil, set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = {"components": components}
    expected_body_schema.update(components["schemas"]["composed"])
    assert operation.body_schema == expected_body_schema


def test_operation_local_security_duplicate_token_info(api):
    components = deepcopy(COMPONENTS)
    components.update({"securitySchemes": SECURITY_DEFINITIONS_BOTH})
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION10,
                          app_security=[],
                          components=components,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    # security decorator should be a partial with verify_oauth_remote as the function and
    # token url and scopes as arguments.
    # See https://docs.python.org/2/library/functools.html#partial-objects

    assert operation.security_decorator.func is verify_oauth_local
    assert operation.security_decorator.args == (math.ceil, set(['uid']))

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
    expected_body_schema = {"components": components}
    expected_body_schema.update(components["schemas"]["composed"])
    assert operation.body_schema == expected_body_schema

def test_non_existent_reference(api):
    with pytest.raises(InvalidSpecification) as exc_info:  # type: py.code.ExceptionInfo
        operation = OpenAPIOperation(api=api,
                              method='GET',
                              path='endpoint',
                              path_parameters=[],
                              operation=OPERATION1,
                              app_security=[],
                              resolver=Resolver())
        operation.body_schema

    exception = exc_info.value
    assert str(exception).startswith("<InvalidSpecification: GET endpoint $ref")
    assert repr(exception).startswith("<InvalidSpecification: GET endpoint $ref")


def test_invalid_reference(api):
    with pytest.raises(InvalidSpecification) as exc_info:  # type: py.code.ExceptionInfo
        components = deepcopy(COMPONENTS)
        operation = OpenAPIOperation(api=api,
                              method='GET',
                              path='endpoint',
                              path_parameters=[],
                              operation=OPERATION3,
                              app_security=[],
                              components=components,
                              resolver=Resolver())
        operation.body_schema

    exception = exc_info.value
    assert str(exception).startswith("<InvalidSpecification: GET endpoint $ref")
    assert repr(exception).startswith("<InvalidSpecification: GET endpoint $ref")


def test_no_token_info(api):
    components = deepcopy(COMPONENTS)
    components.update({"securitySchemes": SECURITY_DEFINITIONS_WO_INFO})
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION1,
                          app_security=SECURITY_DEFINITIONS_WO_INFO,
                          components=components,
                          resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)
    assert operation.security_decorator is security_passthrough

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]

    expected_body_schema = {"components": components}
    expected_body_schema.update(components["schemas"]["new_stack"])
    assert operation.body_schema == expected_body_schema


def test_parameter_reference(api):
    components = deepcopy(COMPONENTS)
    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=OPERATION4,
                          app_security=[],
                          components=components,
                          resolver=Resolver())
    assert operation.parameters == [{'in': 'path', 'schema': {'type': 'integer'}}]


def test_resolve_invalid_reference(api):
    components = deepcopy(COMPONENTS)
    with pytest.raises(InvalidSpecification) as exc_info:
        OpenAPIOperation(api=api,
                  method='GET',
                  path='endpoint',
                  path_parameters=[],
                  operation=OPERATION5,
                  app_security=[],
                  components=components,
                  resolver=Resolver())

    exception = exc_info.value  # type: InvalidSpecification
    assert exception.reason == "GET endpoint '$ref' needs to start with '#/'"


def test_default(api):
    components = deepcopy(COMPONENTS)
    op = OPERATION6.copy()
    op['requestBody']['default'] = 1
    OpenAPIOperation(api=api,
              method='GET',
              path='endpoint',
              path_parameters=[],
              operation=op,
              app_security=[],
              components=components,
              resolver=Resolver())
    op = OPERATION8.copy()
    op['requestBody']['default'] = {
        'keep_stacks': 1, 'image_version': 'one', 'senza_yaml': 'senza.yaml', 'new_traffic': 100
    }
    OpenAPIOperation(api=api,
              method='POST',
              path='endpoint',
              path_parameters=[],
              operation=op,
              app_security=[],
              components=components,
              resolver=Resolver())


def test_get_path_parameter_types(api):
    op = OPERATION1.copy()
    components = deepcopy(COMPONENTS)
    op['parameters'] = [
        {'in': 'path', 'schema': {'type': 'int'}, 'name': 'int_path'},
        {'in': 'path', 'schema': {'type': 'string'}, 'name': 'string_path'},
        {'in': 'path', 'schema': {'type': 'string', 'format': 'path'}, 'name': 'path_path'}]

    operation = OpenAPIOperation(api=api,
                          method='GET',
                          path='endpoint',
                          path_parameters=[],
                          operation=op,
                          components=components,
                          resolver=Resolver())

    assert {'int_path': 'int', 'string_path': 'string', 'path_path': 'path'} == operation.get_path_parameter_types()
