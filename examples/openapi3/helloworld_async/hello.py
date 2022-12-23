import connexion
from starlette.responses import PlainTextResponse


async def test():
    pass


async def post_greeting(name: str) -> PlainTextResponse:
    await test()
    return f"Hello {name}", 201


app = connexion.AsyncApp(__name__, port=9090, specification_dir="openapi/")
app.add_api("helloworld-api.yaml", arguments={"title": "Hello World Example"})
