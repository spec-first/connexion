#!/usr/bin/env python3
'''
Connexion HTTP Basic Auth example

Most of the code stolen from http://flask.pocoo.org/snippets/8/
'''

import connexion
import flask
from functools import wraps


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'admin' and password == 'secret'


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return flask.Response('You have to login with proper credentials', 401,
                          {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = flask.request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@requires_auth
def get_secret() -> str:
    return 'This is a very secret string requiring authentication!'

if __name__ == '__main__':
    app = connexion.App(__name__)
    app.add_api('swagger.yaml')
    app.run(port=8080)
