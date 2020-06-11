from sanic import Sanic

from connexion import SanicApp, SanicApi


def test_sanic_app_default_params():
    app = SanicApp("MyApp")
    assert app.import_name == "MyApp"
    assert app.server == "sanic"
    assert app.api_cls == SanicApi
    assert app.arguments == {}
    # debug should be None so that user can use Sanic environment variables to set it
    assert app.debug is None
    assert app.host is None
    assert app.port is None
    assert app.resolver is None
    assert app.resolver_error is None
    assert not app.auth_all_paths
    assert type(app.app) == Sanic
