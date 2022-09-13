#!/usr/bin/env python3

import connexion


def post_greeting(body: dict) -> str:
    print(body)
    return f"Hello {body['name']}"


if __name__ == "__main__":
    app = connexion.App(__name__, port=9090, specification_dir="openapi/")
    app.add_api("helloworld-api.yaml", arguments={"title": "Hello World Example"})
    app.run()
