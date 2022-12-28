"""
Basic example of a resource server
"""
from pathlib import Path

import connexion
from connexion.exceptions import OAuthProblem

TOKEN_DB = {"asdf1234567890": {"uid": 100}}


def apikey_auth(token, required_scopes):
    info = TOKEN_DB.get(token, None)

    if not info:
        raise OAuthProblem("Invalid token")

    return info


def get_secret(user) -> str:
    return f"You are {user} and the secret is 'wbevuec'"


app = connexion.FlaskApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml")
app.add_api("swagger.yaml")


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
