#!/usr/bin/env python3


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
