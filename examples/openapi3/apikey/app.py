#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import connexion
from connexion.decorators.security import validate_scope
from connexion.exceptions import OAuthScopeProblem

TOKEN_DB = {
    'asdf1234567890': {
        'uid': 100,
        'scope': ['secret'],
    }
}


def apikey_auth(token, required_scopes):
    info = TOKEN_DB.get(token, {})

    # TODO: openapi spec doesn't support scopes for `apiKey` securitySchemes
    # https://swagger.io/docs/specification/authentication/#scopes
    if required_scopes is not None and not validate_scope(required_scopes, info.get('scope', [])):
        raise OAuthScopeProblem(
                description='Provided user doesn\'t have the required access rights',
                required_scopes=required_scopes,
                token_scopes=info['scope']
            )

    return info


def get_secret(user) -> str:
    return "You are {user} and the secret is 'wbevuec'".format(user=user)


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml')
    app.run(port=8080)
