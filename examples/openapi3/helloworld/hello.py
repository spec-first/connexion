#!/usr/bin/env python3

import connexion
from starlette.responses import PlainTextResponse


async def post_greeting(name: str) -> PlainTextResponse:
    return PlainTextResponse(f"Hello {name}")


# if __name__ == "__main__":
app = connexion.AsyncApp(__name__, port=9090, specification_dir="openapi/")
app.add_api("helloworld-api.yaml", arguments={"title": "Hello World Example"})
# app.run()
