#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import connexion


def basic_auth(username, password, required_scopes=None):
    if username == 'admin' and password == 'secret':
        return {'sub': 'admin'}

    # optional: raise exception for custom error response
    return None


def get_secret(user) -> str:
    return "You are {user} and the secret is 'wbevuec'".format(user=user)


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml')
    app.run(port=8080)
