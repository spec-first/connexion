"""
Basic example of a resource server
"""
from pathlib import Path

import connexion

PASSWD = {"admin": "secret", "foo": "bar"}


def basic_auth(username, password):
    if PASSWD.get(username) == password:
        return {"sub": username}
    # optional: raise exception for custom error response
    return None


def get_secret(user) -> str:
    return f"You are {user} and the secret is 'wbevuec'"


app = connexion.FlaskApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml")
app.add_api("swagger.yaml")


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
