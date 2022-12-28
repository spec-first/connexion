"""
Basic example of a resource server
"""
from pathlib import Path

import connexion


def get_secret(user) -> str:
    return f"You are: {user}"


app = connexion.FlaskApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml")
app.add_api("swagger.yaml")


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
