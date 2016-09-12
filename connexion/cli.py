import logging
import sys
from os import path

import click
from clickclick import AliasedGroup, fatal_error
from connexion import App, problem
from connexion.resolver import StubResolver

main = AliasedGroup(context_settings=dict(help_option_names=[
    '-h', '--help']))


def validate_wsgi_server_requirements(ctx, param, value):
    if value == 'gevent':
        try:
            import gevent  # NOQA
        except:
            fatal_error('gevent library is not installed')
    elif value == 'tornado':
        try:
            import tornado  # NOQA
        except:
            fatal_error('tornado library is not installed')


@main.command()
@click.argument('spec_file')
@click.argument('base_path', required=False)
@click.option('--port', '-p', default=5000, type=int, help='Port to listen.')
@click.option('--wsgi-server', '-w', default='flask',
              type=click.Choice(['flask', 'gevent', 'tornado']),
              callback=validate_wsgi_server_requirements,
              help='Which WSGI server container to use.')
@click.option('--stub',
              help='Returns status code 400, and `Not Implemented Yet` payload, for '
              'the endpoints which handlers are not found.',
              is_flag=True, default=False)
@click.option('--hide-spec',
              help='Hides the API spec in JSON format which is by default available at `/swagger.json`.',
              is_flag=True, default=False)
@click.option('--hide-console-ui',
              help='Hides the the API console UI which is by default available at `/ui`.',
              is_flag=True, default=False)
@click.option('--console-ui-url', metavar='URL',
              help='Personalize what URL path the API console UI will be mounted.')
@click.option('--console-ui-from', metavar='PATH',
              help='Path to a customized API console UI dashboard.')
@click.option('--auth-all-paths',
              help='Enable authentication to paths not defined in the spec.',
              is_flag=True, default=False)
@click.option('--validate-responses',
              help='Enable validation of response values from operation handlers.',
              is_flag=True, default=False)
@click.option('--strict-validation',
              help='Enable strict validation of request payloads.',
              is_flag=True, default=False)
@click.option('--debug', '-d', help='Show debugging information.',
              is_flag=True, default=False)
def run(spec_file,
        base_path,
        port,
        wsgi_server,
        stub,
        hide_spec,
        hide_console_ui,
        console_ui_url,
        console_ui_from,
        auth_all_paths,
        validate_responses,
        strict_validation,
        debug):
    """
    Runs a server compliant with a OpenAPI/Swagger 2.0 Specification file.

    Arguments:

    - SPEC_FILE: specification file that describes the server endpoints.

    - BASE_PATH (optional): filesystem path where the API endpoints handlers are going to be imported from.
    """
    logging_level = logging.ERROR
    if debug:
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level)

    sys.path.insert(1, path.abspath(base_path or '.'))

    resolver = None
    if stub:
        resolver = StubResolver(lambda: problem(
            title='Not Implemented Yet',
            detail='The requested functionality is not implemented yet.',
            status=400))

    app = App(__name__)
    app.add_api(path.abspath(spec_file), resolver=resolver)
    app.run(
        port=port,
        server=wsgi_server,
        swagger_json=hide_spec or None,
        swagger_ui=hide_console_ui or None,
        swagger_path=console_ui_from or None,
        swagger_url=console_ui_url or None,
        strict_validation=strict_validation,
        validate_responses=validate_responses,
        auth_all_paths=auth_all_paths,
        debug=debug)
