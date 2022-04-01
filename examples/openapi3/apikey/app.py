#!/usr/bin/env python3
"""
Basic example of a resource server
"""

import especifico
from especifico.exceptions import OAuthProblem

TOKEN_DB = {"asdf1234567890": {"uid": 100}}


def apikey_auth(token, required_scopes):
    info = TOKEN_DB.get(token, None)

    if not info:
        raise OAuthProblem("Invalid token")

    return info


def get_secret(user) -> str:
    return f"You are {user} and the secret is 'wbevuec'"


if __name__ == "__main__":
    app = especifico.FlaskApp(__name__)
    app.add_api("openapi.yaml")
    app.run(port=8080)
