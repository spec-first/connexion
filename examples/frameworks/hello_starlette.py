import typing as t
from pathlib import Path

import connexion
from connexion.decorators import StarletteDecorator
from connexion.resolver import RelativeResolver
from starlette.applications import Starlette
from starlette.routing import Route


@StarletteDecorator()
def post_greeting(name: str, number: t.Optional[int] = None) -> str:
    return f"Hello {name}, your number is {number}!"


app = Starlette(
    debug=True,
    routes=[
        Route("/openapi/greeting/{name}", post_greeting, methods=["POST"]),
        Route("/swagger/greeting/{name}", post_greeting, methods=["POST"]),
    ],
)

app = connexion.ConnexionMiddleware(
    app,
    specification_dir="spec/",
    resolver=RelativeResolver("hello_starlette"),
)
app.add_api("openapi.yaml", arguments={"title": "Hello World Example"})
app.add_api("swagger.yaml", arguments={"title": "Hello World Example"})


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
