#!/usr/bin/env python3
'''
Connexion HTTP Basic Auth example

Most of the code stolen from http://flask.pocoo.org/snippets/8/

Warning: It is recommended to use 'decorator' package to create decorators for
         your view functions to keep Connexion working as expected. For more
         details please check: https://github.com/zalando/connexion/issues/142
'''

import connexion
import flask

try:
    from decorator import decorator
except ImportError:
    import sys
    import logging
    logging.error('Missing dependency. Please run `pip install decorator`')
    sys.exit(1)


def check_auth(username: str, password: str):
    '''This function is called to check if a username /
    password combination is valid.'''
    return username == 'admin' and password == 'secret'


def authenticate():
    '''Sends a 401 response that enables basic auth'''
    return flask.Response('You have to login with proper credentials', 401,
                          {'WWW-Authenticate': 'Basic realm="Login Required"'})


@decorator
def requires_auth(f: callable, *args, **kwargs):
    auth = flask.request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    return f(*args, **kwargs)


@requires_auth
def get_secret() -> str:
    return 'This is a very secret string requiring authentication!'

if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml')
    app.run(port=8080)
