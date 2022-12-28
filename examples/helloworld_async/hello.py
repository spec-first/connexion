from pathlib import Path

import connexion


async def test():
    pass


async def post_greeting(name: str):
    await test()
    return f"Hello {name}", 201


app = connexion.AsyncApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml", arguments={"title": "Hello World Example"})
app.add_api("swagger.yaml", arguments={"title": "Hello World Example"})


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
