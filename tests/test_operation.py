import pathlib

from connexion.operation import Operation

TEST_FOLDER = pathlib.Path(__file__).parent

DEFINITIONS = {'definitions': {'new_stack': {'required': ['image_version', 'keep_stacks', 'new_traffic', 'senza_yaml'],
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
                                                                                'Percentage of the traffic'}}}}}

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


def test_operation():
    operation = Operation(method='GET',
                          path='endpoint',
                          operation=OPERATION1,
                          app_produces=['application/json'],
                          app_security=[],
                          security_definitions={})
    assert operation.method == 'GET'
    assert operation.produces == ['application/json']
    assert operation.security == [{'oauth': ['uid']}]
