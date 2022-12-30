from pathlib import Path

import connexion


def post_greeting(name: str) -> str:
    return f"Hello {name}"


app = connexion.FlaskApp(__name__, specification_dir="spec/")
app.add_api("openapi.yaml", arguments={"title": "Hello World Example"})
app.add_api("swagger.yaml", arguments={"title": "Hello World Example"})


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
