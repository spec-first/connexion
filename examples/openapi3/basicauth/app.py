#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import connexion

PASSWD={
    'admin': 'secret',
    'foo': 'bar'
}

def basic_auth(username, password, required_scopes=None) -> dict:
    if PASSWD.get(username) == password:
        return {'sub': username}
    return None

def get_secret(user) -> str:
    return f"You are {user} and the secret is 'wbevuec'"


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml')
    app.run(port=8080)
