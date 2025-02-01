import logging

from . import conn_app

# reuse the configured logger
logger = logging.getLogger("uvicorn.error")


def post_greeting(name: str, body: dict) -> tuple:
    logger.info(
        "%s: name len %d, body items %d", post_greeting.__name__, len(name), len(body)
    )
    # the body is optional
    message = body.get("message", None)
    if "crash" == message:
        raise ValueError(f"Raise exception for {name}")
    if "invalid" == message:
        return {"bogus": "response"}
    return {"greeting": f"Hello {name}"}, 200


def main() -> None:
    # ensure logging is configured
    logging.basicConfig(level=logging.DEBUG)
    # launch the app using the dev server
    conn_app.run("hello:conn_app", port=8080)


if __name__ == "__main__":
    main()
