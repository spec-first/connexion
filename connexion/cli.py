import logging
import sys
from os import path

import click
from clickclick import AliasedGroup, fatal_error

import connexion
from connexion.mock import MockResolver

logger = logging.getLogger('connexion.cli')
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


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


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Connexion {}'.format(connexion.__version__))
    ctx.exit()


@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.option('-V', '--version', is_flag=True, callback=print_version, expose_value=False, is_eager=True,
              help='Print the current version number and exit.')
def main():
    pass


@main.command()
@click.argument('spec_file')
@click.argument('base_module_path', required=False)
@click.option('--port', '-p', default=5000, type=int, help='Port to listen.')
@click.option('--host', '-H', type=str, help='Host interface to bind on.')
@click.option('--wsgi-server', '-w', default='flask',
              type=click.Choice(['flask', 'gevent', 'tornado']),
              callback=validate_wsgi_server_requirements,
              help='Which WSGI server container to use.')
@click.option('--stub',
              help='Returns status code 501, and `Not Implemented Yet` payload, for '
              'the endpoints which handlers are not found.',
              is_flag=True, default=False)
@click.option('--mock', metavar='MOCKMODE', type=click.Choice(['all', 'notimplemented']),
              help='Returns example data for all endpoints or for which handlers are not found.')
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
@click.option('--verbose', '-v', help='Show verbose information.', count=True)
@click.option('--base-path', metavar='PATH',
              help='Override the basePath in the API spec.')
def run(spec_file,
        base_module_path,
        port,
        host,
        wsgi_server,
        stub,
        mock,
        hide_spec,
        hide_console_ui,
        console_ui_url,
        console_ui_from,
        auth_all_paths,
        validate_responses,
        strict_validation,
        debug,
        verbose,
        base_path):
    """
    Runs a server compliant with a OpenAPI/Swagger 2.0 Specification file.

    Arguments:

    - SPEC_FILE: specification file that describes the server endpoints.

    - BASE_MODULE_PATH (optional): filesystem path where the API endpoints handlers are going to be imported from.
    """
    logging_level = logging.WARN
    if verbose > 0:
        logging_level = logging.INFO

    if debug or verbose > 1:
        logging_level = logging.DEBUG
        debug = True

    logging.basicConfig(level=logging_level)

    spec_file_full_path = path.abspath(spec_file)
    py_module_path = base_module_path or path.dirname(spec_file_full_path)
    sys.path.insert(1, path.abspath(py_module_path))
    logger.debug('Added {} to system path.'.format(py_module_path))

    resolver_error = None
    if stub:
        resolver_error = 501

    api_extra_args = {}
    if mock:
        resolver = MockResolver(mock_all=mock == 'all')
        api_extra_args['resolver'] = resolver

    app = connexion.FlaskApp(__name__,
                             swagger_json=not hide_spec,
                             swagger_ui=not hide_console_ui,
                             swagger_path=console_ui_from or None,
                             swagger_url=console_ui_url or None,
                             auth_all_paths=auth_all_paths,
                             debug=debug)

    app.add_api(spec_file_full_path,
                base_path=base_path,
                resolver_error=resolver_error,
                validate_responses=validate_responses,
                strict_validation=strict_validation,
                **api_extra_args)

    app.run(port=port,
            host=host,
            server=wsgi_server,
            debug=debug)


if __name__ == '__main__':  # pragma: no cover
    main()
