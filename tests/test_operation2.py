import copy
import logging
import math
import pathlib
import types
from unittest import mock

import pytest
from connexion.apis.flask_api import Jsonifier
from connexion.exceptions import InvalidSpecification
from connexion.json_schema import resolve_refs
from connexion.middleware.security import SecurityOperation
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

OPERATION9 = {'description': 'operation secured with 2 api keys',
                'operationId': 'fakeapi.hello.post_greeting',
                'responses': {'200': {'description': 'OK'}},
                'security': [{'key1': [], 'key2': []}]}

OPERATION10 = {'description': 'operation secured with 2 oauth schemes combined using logical AND',
                'operationId': 'fakeapi.hello.post_greeting',
                'responses': {'200': {'description': 'OK'}},
                'security': [{'oauth_1': ['uid'], 'oauth_2': ['uid']}]}

OPERATION11 = {'description': 'operation secured with an oauth schemes with 2 possible scopes (in OR)',
                'operationId': 'fakeapi.hello.post_greeting',
                'responses': {'200': {'description': 'OK'}},
                'security': [{'oauth': ['myscope']}, {'oauth': ['myscope2']}]}

SECURITY_DEFINITIONS_REMOTE = {'oauth': {'type': 'oauth2',
                                         'flow': 'password',
                                         'x-tokenInfoUrl': 'https://oauth.example/token_info',
                                         'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_LOCAL = {'oauth': {'type': 'oauth2',
                                        'flow': 'password',
                                        'x-tokenInfoFunc': 'math.ceil',
                                        'scopes': {'myscope': 'can do stuff',
                                                   'myscope2': 'can do other stuff'}}}

SECURITY_DEFINITIONS_BOTH = {'oauth': {'type': 'oauth2',
                                       'flow': 'password',
                                       'x-tokenInfoFunc': 'math.ceil',
                                       'x-tokenInfoUrl': 'https://oauth.example/token_info',
                                       'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_WO_INFO = {'oauth': {'type': 'oauth2',
                                          'flow': 'password',
                                          'scopes': {'myscope': 'can do stuff'}}}

SECURITY_DEFINITIONS_2_KEYS = {'key1': {'type': 'apiKey',
                                        'in': 'header',
                                        'name': 'X-Auth-1',
                                        'x-apikeyInfoFunc': 'math.ceil'},
                               'key2': {'type': 'apiKey',
                                        'in': 'header',
                                        'name': 'X-Auth-2',
                                        'x-apikeyInfoFunc': 'math.ceil'}}

SECURITY_DEFINITIONS_2_OAUTH = {'oauth_1': {'type': 'oauth2',
                                            'flow': 'password',
                                            'x-tokenInfoFunc': 'math.ceil',
                                            'scopes': {'myscope': 'can do stuff'}},
                                'oauth_2': {'type': 'oauth2',
                                            'flow': 'password',
                                            'x-tokenInfoFunc': 'math.ceil',
                                            'scopes': {'myscope': 'can do stuff'}}}


@pytest.fixture
def api(security_handler_factory):
    api = mock.MagicMock(jsonifier=Jsonifier)
    api.security_handler_factory = security_handler_factory
    yield api


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


def test_operation(api, security_handler_factory):
    op_spec = make_operation(OPERATION1)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  definitions=DEFINITIONS,
                                  resolver=Resolver())

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']

    expected_body_schema = op_spec["parameters"][0]["schema"]
    expected_body_schema.update({'definitions': DEFINITIONS})
    assert operation.body_schema == expected_body_schema


def test_operation_remote_token_info(security_handler_factory):
    verify_oauth = mock.MagicMock(return_value='verify_oauth_result')
    security_handler_factory.verify_oauth = verify_oauth
    security_handler_factory.get_token_info_remote = mock.MagicMock(return_value='get_token_info_remote_result')

    SecurityOperation(security_handler_factory=security_handler_factory,
                      security=[{'oauth': ['uid']}],
                      security_schemes=SECURITY_DEFINITIONS_REMOTE)

    verify_oauth.assert_called_with('get_token_info_remote_result',
                                    security_handler_factory.validate_scope,
                                    ['uid'])
    security_handler_factory.get_token_info_remote.assert_called_with('https://oauth.example/token_info')


def test_operation_array(api):
    op_spec = make_operation(OPERATION7)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  definitions=DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']

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
                                  definitions=DEFINITIONS,
                                  resolver=Resolver())
    assert isinstance(operation.function, types.FunctionType)

    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.consumes == ['application/json']

    expected_body_schema = op_spec["parameters"][0]["schema"]
    expected_body_schema.update({'definitions': DEFINITIONS})
    assert operation.body_schema == expected_body_schema


def test_operation_local_security_oauth2(security_handler_factory):
    verify_oauth = mock.MagicMock(return_value='verify_oauth_result')
    security_handler_factory.verify_oauth = verify_oauth

    SecurityOperation(security_handler_factory=security_handler_factory,
                      security=[{'oauth': ['uid']}],
                      security_schemes=SECURITY_DEFINITIONS_LOCAL)

    verify_oauth.assert_called_with(math.ceil, security_handler_factory.validate_scope, ['uid'])


def test_operation_local_security_duplicate_token_info(security_handler_factory):
    verify_oauth = mock.MagicMock(return_value='verify_oauth_result')
    security_handler_factory.verify_oauth = verify_oauth

    SecurityOperation(security_handler_factory,
                      security=[{'oauth': ['uid']}],
                      security_schemes=SECURITY_DEFINITIONS_BOTH)

    verify_oauth.call_args.assert_called_with(math.ceil, security_handler_factory.validate_scope)


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
                                      definitions=DEFINITIONS,
                                      resolver=Resolver())
        operation.body_schema

    exception = exc_info.value
    assert str(exception) == "GET endpoint There can be one 'body' parameter at most"
    assert repr(exception) == """<InvalidSpecification: "GET endpoint There can be one 'body' parameter at most">"""


def test_no_token_info(security_handler_factory):
    SecurityOperation(security_handler_factory=security_handler_factory,
                      security=[{'oauth': ['uid']}],
                      security_schemes=SECURITY_DEFINITIONS_WO_INFO)


def test_multiple_security_schemes_and(security_handler_factory):
    """Tests an operation with multiple security schemes in AND fashion."""
    def return_api_key_name(func, in_, name):
        return name
    verify_api_key = mock.MagicMock(side_effect=return_api_key_name)
    security_handler_factory.verify_api_key = verify_api_key
    verify_multiple = mock.MagicMock(return_value='verify_multiple_result')
    security_handler_factory.verify_multiple_schemes = verify_multiple

    security = [{'key1': [], 'key2': []}]

    SecurityOperation(security_handler_factory=security_handler_factory,
                      security=security,
                      security_schemes=SECURITY_DEFINITIONS_2_KEYS)

    assert verify_api_key.call_count == 2
    verify_api_key.assert_any_call(math.ceil, 'header', 'X-Auth-1')
    verify_api_key.assert_any_call(math.ceil, 'header', 'X-Auth-2')
    # Assert verify_multiple_schemes is called with mapping from scheme name
    # to result of security_handler_factory.verify_api_key()
    verify_multiple.assert_called_with({'key1': 'X-Auth-1', 'key2': 'X-Auth-2'})


def test_multiple_oauth_in_and(security_handler_factory, caplog):
    """Tests an operation with multiple oauth security schemes in AND fashion.
    These should be ignored and raise a warning.
    """
    caplog.set_level(logging.WARNING, logger="connexion.operations.secure")
    verify_oauth = mock.MagicMock(return_value='verify_oauth_result')
    security_handler_factory.verify_oauth = verify_oauth

    security = [{'oauth_1': ['uid'], 'oauth_2': ['uid']}]

    SecurityOperation(security_handler_factory=security_handler_factory,
                      security=security,
                      security_schemes=SECURITY_DEFINITIONS_2_OAUTH)

    assert '... multiple OAuth2 security schemes in AND fashion not supported' in caplog.text


def test_parameter_reference(api):
    op_spec = make_operation(OPERATION3, definitions=False)
    operation = Swagger2Operation(api=api,
                                  method='GET',
                                  path='endpoint',
                                  path_parameters=[],
                                  operation=op_spec,
                                  app_produces=['application/json'],
                                  app_consumes=['application/json'],
                                  definitions={},
                                  resolver=Resolver())
    assert operation.parameters == [{'in': 'path', 'type': 'integer'}]


def test_default(api):
    op_spec = make_operation(OPERATION4)
    op_spec['parameters'][1]['default'] = 1
    Swagger2Operation(
        api=api, method='GET', path='endpoint', path_parameters=[],
        operation=op_spec, app_produces=['application/json'],
        app_consumes=['application/json'], definitions=DEFINITIONS,
        resolver=Resolver()
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
        app_consumes=['application/json'], definitions=DEFINITIONS,
        resolver=Resolver()
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


def test_oauth_scopes_in_or(security_handler_factory):
    """Tests whether an OAuth security scheme with 2 different possible scopes is correctly handled."""
    verify_oauth = mock.MagicMock(return_value='verify_oauth_result')
    security_handler_factory.verify_oauth = verify_oauth
    
    security = [{'oauth': ['myscope']}, {'oauth': ['myscope2']}]

    SecurityOperation(security_handler_factory=security_handler_factory,
                      security=security,
                      security_schemes=SECURITY_DEFINITIONS_LOCAL)

    verify_oauth.assert_has_calls([
        mock.call(math.ceil, security_handler_factory.validate_scope, ['myscope']),
        mock.call(math.ceil, security_handler_factory.validate_scope, ['myscope2']),
    ])
