import logging
import sys
from os import path

import click
from connexion import App

from clickclick import AliasedGroup

main = AliasedGroup(context_settings=dict(help_option_names=[
    '-h', '--help']))


@main.command()
@click.argument('spec_file')
@click.argument('base_path', required=False)
@click.option('--port', '-p', default=5000, type=int, help='Port to listen.')
@click.option('--server', '-s', default='gevent',
              type=click.Choice(['gevent', 'tornado']),
              help='Which WSGI server to use.')
@click.option('--hide-spec',
              help='Hides the API spec in JSON format which is by default available at `/swagger.json`.',
              is_flag=True, default=True)
@click.option('--hide-swagger-ui',
              help='Hides the the Swagger UI which is by default available at `/ui`.',
              is_flag=True, default=True)
@click.option('--swagger-ui-url', metavar='URL',
              help='Personalize what URL path the Swagger UI will be mounted.')
@click.option('--swagger-ui-from', metavar='PATH',
              help='Path to a customized Swagger UI dashboard.')
@click.option('--auth-all-paths',
              help='Enable authentication to paths not defined in the spec.',
              is_flag=True, default=False)
@click.option('--debug', '-d', help='Show debugging information.',
              is_flag=True, default=False)
def run(spec_file, base_path, port, server, debug):
    """
    Runs a server using the passed OpenAPI/Swagger 2.0 Specification file.

    Possible arguments:

    - SPEC_FILE: specification file of the API to run.

    - BASE_PATH (optional): filesystem path from where to import the API handlers.
    """
    logging_level = logging.ERROR
    if debug:
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level)

    sys.path.insert(1, path.abspath(base_path or '.'))

    app = App(__name__)
    app.add_api(path.abspath(spec_file))
    click.echo('Running at http://localhost:{}/...'.format(port))
    app.run(port=port, server=server)
