#!/usr/bin/env python3

from connexion import problem


def post_greeting(name: str) -> dict:
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return data


def get_list(name: str) -> list:
    data = ['hello', name]
    return data


def get_bye(name: str) -> str:
    return 'Goodbye {name}'.format(name=name), 200


def get_bye_secure(name: str) -> str:
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
