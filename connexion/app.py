import logging
import pathlib

import flask
import tornado.wsgi
import tornado.httpserver
import tornado.ioloop

import connexion.api
import connexion.utils as utils

logger = logging.getLogger('api')

class App:

    def __init__(self, import_name: str, port: int=5000, specification_dir: pathlib.Path=''):
        self.app = flask.Flask(import_name)

        # we get our application root path from flask to avoid duplicating logic
        self.root_path = pathlib.Path(self.app.root_path)
        logger.debug('Root Path: %s', self.root_path)

        specification_dir = pathlib.Path(specification_dir)  # Ensure specification dir is a Path
        if specification_dir.is_absolute():
            self.specification_dir = specification_dir
        else:
            self.specification_dir = self.root_path / specification_dir

        logger.debug('Specification directory: %s', self.specification_dir)

        self.port = port

    def add_api(self, swagger_file: pathlib.Path, base_path: str=None):
        logger.debug('Adding API: %s', swagger_file)
        # TODO test if base_url starts with an / (if not none)

        yaml_path = self.specification_dir / swagger_file
        api = connexion.api.Api(yaml_path, base_path)
        self.app.register_blueprint(api.blueprint)

    def run(self):
        wsgi_container = tornado.wsgi.WSGIContainer(self.app)
        http_server = tornado.httpserver.HTTPServer(wsgi_container)
        http_server.listen(self.port)
        logger.info('Listening on http://127.0.0.1:{port}/'.format(port=self.port))
        tornado.ioloop.IOLoop.instance().start()
