#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import connexion

import flask


def get_secret() -> str:
    # the token's uid will be set in request.user
    return 'You are: {uid}'.format(uid=flask.request.user)

if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('app.yaml')
    app.run(port=8080)
