import typing as t
from pathlib import Path

import connexion
from connexion.decorators import ASGIDecorator
from connexion.resolver import RelativeResolver
from quart import Quart

app = Quart(__name__)


@app.route("/openapi/greeting/<name>", methods=["POST"])
@app.route("/swagger/greeting/<name>", methods=["POST"])
@ASGIDecorator()
def post_greeting(name: str, number: t.Optional[int] = None) -> str:
    return f"Hello {name}, your number is {number}!"


app = connexion.ConnexionMiddleware(
    app,
    specification_dir="spec/",
    resolver=RelativeResolver("hello_quart"),
)
app.add_api("openapi.yaml", arguments={"title": "Hello World Example"})
app.add_api("swagger.yaml", arguments={"title": "Hello World Example"})


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
