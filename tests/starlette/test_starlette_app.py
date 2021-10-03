import logging
import os
import pathlib
from unittest import mock

import pytest
from connexion import StarletteApp
from connexion.exceptions import ConnexionException

from conftest import TEST_FOLDER


@pytest.fixture
def uvicorn_app_mock(monkeypatch):
    mock_ = mock.MagicMock()
    monkeypatch.setattr('uvicorn.run', mock_)
    return mock_


@pytest.fixture
def sys_modules_mock(monkeypatch):
    monkeypatch.setattr('connexion.apps.aiohttp_app.sys.modules', {})


def test_app_run(uvicorn_app_mock, starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.run(use_default_access_log=True)
    assert uvicorn_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host='0.0.0.0')
    ]


def test_app_run_new_port(uvicorn_app_mock, starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.run(port=5002)
    assert uvicorn_app_mock.call_args_list == [
        mock.call(app.app, port=5002, host='0.0.0.0')
    ]


def test_app_run_default_port(uvicorn_app_mock, starlette_api_spec_dir):
    app = StarletteApp(__name__,
                     specification_dir=starlette_api_spec_dir,
                     debug=True)
    app.run()
    assert uvicorn_app_mock.call_args_list == [
        mock.call(app.app, port=5000, host='0.0.0.0')
    ]


def test_app_run_debug(uvicorn_app_mock, starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir)
    app.add_api('swagger_simple.yaml')
    app.run(debug=True)
    assert uvicorn_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host='0.0.0.0')
    ]


def test_app_run_server_error(uvicorn_app_mock, starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir)

    with pytest.raises(Exception) as exc_info:
        app.run(server='other')

    assert exc_info.value.args == ('Server other not recognized',)


def test_app_get_root_path_return_Path(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir)
    assert isinstance(app.get_root_path(), pathlib.Path) == True


def test_app_get_root_path_exists(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir)
    assert app.get_root_path().exists() == True


def test_app_get_root_path(starlette_api_spec_dir):
    app = StarletteApp(__name__, port=5001,
                     specification_dir=starlette_api_spec_dir)
    root_path = app.get_root_path()
    assert str(root_path).endswith(os.path.join('tests', 'starlette')) == True


def test_app_get_root_path_not_in_sys_modules(sys_modules_mock, starlette_api_spec_dir):
    app = StarletteApp('connexion', port=5001,
                     specification_dir=starlette_api_spec_dir)
    root_path = app.get_root_path()
    assert str(root_path).endswith(os.sep + 'connexion') == True


def test_app_get_root_path_invalid(sys_modules_mock, starlette_api_spec_dir):
    with pytest.raises(RuntimeError) as exc_info:
        StarletteApp('error__', port=5001,
                   specification_dir=starlette_api_spec_dir)

    assert exc_info.value.args == ("Invalid import name 'error__'",)


def test_app_with_empty_base_path_and_only_one_api(starlette_api_spec_dir):
    spec_dir = '..' / starlette_api_spec_dir.relative_to(TEST_FOLDER)
    app = StarletteApp(__name__, port=5001,
                     specification_dir=spec_dir,
                     debug=True,
                     only_one_api=True)
    api = app.add_api('swagger_empty_base_path.yaml')
    assert api is app.app


def test_app_add_two_apis_error_with_only_one_api(starlette_api_spec_dir):
    spec_dir = '..' / starlette_api_spec_dir.relative_to(TEST_FOLDER)
    app = StarletteApp(__name__, port=5001,
                     specification_dir=spec_dir,
                     debug=True,
                     only_one_api=True)
    app.add_api('swagger_empty_base_path.yaml')

    with pytest.raises(ConnexionException) as exc_info:
        app.add_api('swagger_empty_base_path.yaml')

    assert exc_info.value.args == (
        "an api was already added, "
        "create a new app with 'only_one_api=False' "
        "to add more than one api",
    )
