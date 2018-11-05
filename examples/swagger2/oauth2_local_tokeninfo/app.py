#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import connexion

# our hardcoded mock "Bearer" access tokens
TOKENS = {
    '123': 'jdoe',
    '456': 'rms'
}


def get_secret(user) -> str:
    return 'You are: {uid}'.format(uid=user)


def token_info(access_token) -> dict:
    uid = TOKENS.get(access_token)
    if not uid:
        return None
    return {'uid': uid, 'scope': ['uid']}


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('app.yaml')
    app.run(port=8080)
