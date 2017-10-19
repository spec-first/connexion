import logging
from unittest import mock

import pytest
from connexion import AioHttpApp


@pytest.fixture
def web_run_app_mock(monkeypatch):
    mock_ = mock.MagicMock()
    monkeypatch.setattr('connexion.apps.aiohttp_app.web.run_app', mock_)
    return mock_


@pytest.fixture
def sys_modules_mock(monkeypatch):
    monkeypatch.setattr('connexion.apps.aiohttp_app.sys.modules', {})


def test_app_run(web_run_app_mock, simple_aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.run(use_default_access_log=True)
    logger = logging.getLogger('connexion.aiohttp_app')
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host='0.0.0.0', access_log=logger)
    ]


def test_app_run_new_port(web_run_app_mock, simple_aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.run(port=5002)
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5002, host='0.0.0.0', access_log=None)
    ]


def test_app_run_default_port(web_run_app_mock, simple_aiohttp_api_spec_dir):
    app = AioHttpApp(__name__,
                     specification_dir=simple_aiohttp_api_spec_dir,
                     debug=True)
    app.run()
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5000, host='0.0.0.0', access_log=None)
    ]


def test_app_run_debug(web_run_app_mock, simple_aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir)
    app.add_api('swagger.yaml')
    app.run(debug=True)
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host='0.0.0.0', access_log=None)
    ]


def test_app_run_server_error(web_run_app_mock, simple_aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir)

    with pytest.raises(Exception) as exc_info:
        app.run(server='other')

    assert exc_info.value.args == ('Server other not recognized',)


def test_app_get_root_path(simple_aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir)
    assert app.get_root_path().endswith('connexion/tests/aiohttp') == True


def test_app_get_root_path_not_in_sys_modules(sys_modules_mock, simple_aiohttp_api_spec_dir):
    app = AioHttpApp('connexion', port=5001,
                     specification_dir=simple_aiohttp_api_spec_dir)
    assert app.get_root_path().endswith('/connexion') == True


def test_app_get_root_path_invalid(sys_modules_mock, simple_aiohttp_api_spec_dir):
    with pytest.raises(RuntimeError) as exc_info:
        AioHttpApp('error__', port=5001,
                   specification_dir=simple_aiohttp_api_spec_dir)

    assert exc_info.value.args == ("Invalid import name 'error__'",)
