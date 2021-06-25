# coding: utf-8
from flask import Flask

from connexion.apis.flask_api import FlaskApi
from connexion.apps.flask_app import FlaskApp


def test_flask_app_default_params():
    app = FlaskApp('MyApp')
    assert app.import_name == 'MyApp'
    assert app.server == 'flask'
    assert app.api_cls == FlaskApi
    assert app.arguments == {}
    # debug should be None so that user can use Flask environment variables to set it
    assert app.debug is None
    assert app.host is None
    assert app.port is None
    assert app.resolver is None
    assert app.resolver_error is None
    assert not app.auth_all_paths
    assert type(app.app) == Flask
