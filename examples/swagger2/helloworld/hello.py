#!/usr/bin/env python3

import especifico


def post_greeting(name: str) -> str:
    return f"Hello {name}"


if __name__ == "__main__":
    app = especifico.FlaskApp(__name__, port=9090, specification_dir="swagger/")
    app.add_api("helloworld-api.yaml", arguments={"title": "Hello World Example"})
    app.run()
