import logging

import connexion
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.problem import problem

logger = logging.getLogger(__name__)


async def handle_error(request: ConnexionRequest, ex: Exception) -> ConnexionResponse:
    """
    Report an error that happened while processing a request.
    See: https://connexion.readthedocs.io/en/latest/exceptions.html

    This function is defined as `async` so it can be called by the
    Connexion asynchronous middleware framework without a wrapper.
    If a plain function is provided, the framework calls the function
    from a threadpool and the exception stack trace is not available.

    :param request: Request that failed
    :parm ex: Exception that was raised
    :return: ConnexionResponse with RFC7087 problem details
    """
    # log the request URL, exception and stack trace
    logger.exception("Request to %s caused exception", request.url)
    return problem(title="Error", status=500, detail=repr(ex))


def create_app() -> connexion.FlaskApp:
    """
    Create the Connexion FlaskApp, which wraps a Flask app.

    :return Newly created FlaskApp
    """
    app = connexion.FlaskApp(__name__, specification_dir="spec/")
    # hook the functions to the OpenAPI spec
    title = {"title": "Hello World Plus Example"}
    app.add_api("openapi.yaml", arguments=title, validate_responses=True)
    app.add_api("swagger.yaml", arguments=title, validate_responses=True)
    # hook an async function that is invoked on any exception
    app.add_error_handler(Exception, handle_error)
    # return the fully initialized FlaskApp
    return app


# create and publish for import by other modules
conn_app = create_app()
