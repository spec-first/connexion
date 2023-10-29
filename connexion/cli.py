"""
This module defines a command-line interface (CLI) that runs an OpenAPI specification to be a
starting point for developing your API with Connexion.
"""

import argparse
import importlib.metadata
import logging
import os
import sys
import typing as t

import connexion
from connexion.apps import AbstractApp
from connexion.mock import MockResolver
from connexion.options import SwaggerUIOptions

logger = logging.getLogger(__name__)

FLASK_APP = "flask"
ASYNC_APP = "async"
AVAILABLE_APPS = {
    FLASK_APP: "connexion.apps.flask.FlaskApp",
    ASYNC_APP: "connexion.apps.asynchronous.AsyncApp",
}


def run(app: AbstractApp, args: argparse.Namespace):
    app.run("connexion.cli:create_app", port=args.port, host=args.host, factory=True)


parser = argparse.ArgumentParser()

parser.add_argument(
    "--version",
    action="version",
    version=f"Connexion {importlib.metadata.version('connexion')}",
)

subparsers = parser.add_subparsers()
run_parser = subparsers.add_parser("run")
run_parser.set_defaults(func=run)

run_parser.add_argument("spec_file", help="Path to OpenAPI specification.")
run_parser.add_argument(
    "base_module_path", nargs="?", help="Root directory of handler code."
)
run_parser.add_argument(
    "-p", "--port", default=5000, type=int, help="Port to listen on."
)
run_parser.add_argument(
    "-H", "--host", default="127.0.0.1", type=str, help="Host interface to bind on."
)
run_parser.add_argument(
    "--stub",
    action="store_true",
    help="Returns status code 501, and `Not Implemented Yet` payload, for the endpoints which "
    "handlers are not found.",
)
run_parser.add_argument(
    "--mock",
    choices=["all", "notimplemented"],
    help="Returns example data for all endpoints or for which handlers are not found.",
)
run_parser.add_argument(
    "--swagger-ui-path",
    help="Personalize what URL path the API console UI will be mounted.",
    default="/ui",
)
run_parser.add_argument(
    "--swagger-ui-template-dir",
    help="Path to a customized API console UI dashboard.",
)
run_parser.add_argument(
    "--auth-all-paths",
    help="Enable authentication to paths not defined in the spec.",
    action="store_true",
)
run_parser.add_argument(
    "--validate-responses",
    help="Enable validation of response values from operation handlers.",
    action="store_true",
)
run_parser.add_argument(
    "--strict-validation",
    help="Enable strict validation of request payloads.",
    action="store_true",
)
run_parser.add_argument(
    "-v",
    "--verbose",
    help="Show verbose information.",
    action="count",
    default=0,
)
run_parser.add_argument("--base-path", help="Override the basePath in the API spec.")
run_parser.add_argument(
    "--app-framework",
    "-f",
    choices=list(AVAILABLE_APPS),
    default=ASYNC_APP,
    help="The app framework used to run the server",
)


def create_app(args: t.Optional[argparse.Namespace] = None) -> AbstractApp:
    """Runs a server compliant with a OpenAPI/Swagger Specification file."""
    if args is None:
        args = parser.parse_args()

    if args.verbose == 1:
        logging_level = logging.INFO
    elif args.verbose >= 2:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.WARN

    logging.basicConfig(level=logging_level)

    spec_file_full_path = os.path.abspath(args.spec_file)
    py_module_path = args.base_module_path or os.path.dirname(spec_file_full_path)
    sys.path.insert(1, os.path.abspath(py_module_path))
    logger.debug(f"Added {py_module_path} to system path.")

    resolver_error = None
    if args.stub:
        resolver_error = 501

    api_extra_args = {}
    if args.mock:
        resolver = MockResolver(mock_all=args.mock == "all")
        api_extra_args["resolver"] = resolver

    app_cls = connexion.utils.get_function_from_name(AVAILABLE_APPS[args.app_framework])

    swagger_ui_options = SwaggerUIOptions(
        swagger_ui_path=args.swagger_ui_path,
        swagger_ui_template_dir=args.swagger_ui_template_dir,
    )

    app = app_cls(
        __name__,
        auth_all_paths=args.auth_all_paths,
        swagger_ui_options=swagger_ui_options,
    )

    app.add_api(
        spec_file_full_path,
        base_path=args.base_path,
        resolver_error=resolver_error,
        validate_responses=args.validate_responses,
        strict_validation=args.strict_validation,
        **api_extra_args,
    )

    return app


def main(argv: t.Optional[t.List[str]] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["--help"]

    args = parser.parse_args(argv)
    app = create_app(args)
    args.func(app, args)
