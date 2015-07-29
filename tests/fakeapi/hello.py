#!/usr/bin/env python3

from connexion import problem


def post_greeting(name):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return data


def get_list(name):
    data = ['hello', name]
    return data


def get_bye(name):
    return 'Goodbye {name}'.format(name=name), 200


def get_bye_secure(name):
    return 'Goodbye {name} (Secure)'.format(name=name)


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


def schema():
    return ''


def schema_list():
    return ''
