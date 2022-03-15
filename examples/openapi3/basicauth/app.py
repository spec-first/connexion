#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import connexion


def basic_auth(username, password, required_scopes=None):
    if username == 'admin' and password == 'secret':
        info = {'sub': 'admin', 'scope': 'secret'}
    elif username == 'foo' and password == 'bar':
        info = {'sub': 'user1', 'scope': ''}
    else:
        # optional: raise exception for custom error response
        return None

    return info


def get_secret(user) -> str:
    return f"You are {user} and the secret is 'wbevuec'"


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml')
    app.run(port=8080)
