#!/usr/bin/env python3

from connexion import problem, request


def post_greeting(name):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return data

def post_goodday(name):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    headers = [("Location", "/my/uri")]
    return data, 201, headers

def get_list(name):
    data = ['hello', name]
    return data


def get_bye(name):
    return 'Goodbye {name}'.format(name=name), 200


def get_bye_secure(name):
    return 'Goodbye {name} (Secure: {user})'.format(name=name, user=request.user)


def with_problem():
    return problem(type='http://www.example.com/error',
                   title='Some Error',
                   detail='Something went wrong somewhere',
                   status=418,
                   instance='instance1')


def with_problem_txt():
    return problem(title='Some Error',
                   detail='Something went wrong somewhere',
                   status=418,
                   instance='instance1')


def internal_error():
    return 42 / 0


def get_greetings(name):
    """
    Used to test custom mimetypes
    """
    data = {'greetings': 'Hello {name}'.format(name=name)}
    return data


def multimime():
    return 'Goodbye'


def empty():
    return None, 204


def schema(new_stack):
    return new_stack


def schema_query(image_version=None):
    return {'image_version': image_version}


def schema_list():
    return ''


def schema_format():
    return ''


def test_parameter_validation():
    return ''


def test_required_query_param():
    return ''


def test_schema_array(test_array):
    return test_array


def test_schema_int(test_int):
    return test_int
