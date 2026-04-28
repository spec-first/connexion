import logging
from pathlib import Path

from connexion import FlaskApp
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.problem import problem

# reuse the configured logger for simplicity
logger = logging.getLogger("uvicorn.error")


def handle_error(request: ConnexionRequest, ex: Exception) -> ConnexionResponse:
    """
    Report an error that happened while processing a request.
    See: https://connexion.readthedocs.io/en/latest/exceptions.html

    :param request: Request that failed
    :parm ex: Exception that was raised
    :return: ConnexionResponse with RFC7087 problem details
    """
    # log the request URL, exception and stack trace
    logger.exception(
        "Connexion caught exception on request to %s", request.url, exc_info=ex
    )
    return problem(title="Error", status=500, detail=repr(ex))


def create_app() -> FlaskApp:
    """
    Create the connexion.FlaskApp, which wraps a Flask app.

    :return Newly created connexion.FlaskApp
    """
    app = FlaskApp(__name__, specification_dir="spec/")
    # hook the functions to the OpenAPI spec
    title = {"title": "Hello World Plus Example"}
    app.add_api("openapi.yaml", arguments=title, validate_responses=True)
    app.add_api("swagger.yaml", arguments=title, validate_responses=True)
    # hook a function that is invoked on any exception
    app.add_error_handler(Exception, handle_error)
    # return the fully initialized connexion.FlaskApp
    return app


def post_greeting(name: str, body: dict) -> tuple:
    logger.info(
        "%s: name len %d, body items %d", post_greeting.__name__, len(name), len(body)
    )
    # the body is optional
    message = body.get("message", None)
    if "crash" == message:
        msg = f"Found message {message}, raise ValueError"
        logger.info("%s", msg)
        raise ValueError(msg)
    if "invalid" == message:
        logger.info("Found message %s, return invalid response", message)
        return {"bogus": "response"}
    return {"greeting": f"Hello {name}"}, 200


# define app so loader can find it
conn_app = create_app()
if __name__ == "__main__":
    conn_app.run(f"{Path(__file__).stem}:conn_app", port=8080)
