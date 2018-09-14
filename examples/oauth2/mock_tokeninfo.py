#!/usr/bin/env python3
'''
Mock OAuth2 token info
'''

import connexion
from connexion import request

# our hardcoded mock "Bearer" access tokens
TOKENS = {
    '123': 'jdoe',
    '456': 'rms'
}


def get_tokeninfo() -> dict:
    try:
        _, access_token = request.headers['Authorization'].split()
    except Exception:
        access_token = ''

    uid = TOKENS.get(access_token)

    if not uid:
        return 'No such token', 401

    return {'uid': uid, 'scope': ['uid']}


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('mock_tokeninfo.yaml')
    app.run(port=7979)
