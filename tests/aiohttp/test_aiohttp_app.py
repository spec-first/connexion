import logging
import os
import pathlib
from unittest import mock

from conftest import TEST_FOLDER
import pytest

from especifico import AioHttpApp
from especifico.exceptions import EspecificoException


@pytest.fixture
def web_run_app_mock(monkeypatch):
    mock_ = mock.MagicMock()
    monkeypatch.setattr("especifico.apps.aiohttp_app.web.run_app", mock_)
    return mock_


@pytest.fixture
def sys_modules_mock(monkeypatch):
    monkeypatch.setattr("especifico.apps.aiohttp_app.sys.modules", {})


def test_app_run(web_run_app_mock, aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True)
    app.run(use_default_access_log=True)
    logger = logging.getLogger("especifico.aiohttp_app")
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host="0.0.0.0", access_log=logger),
    ]


def test_app_run_new_port(web_run_app_mock, aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True)
    app.run(port=5002)
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5002, host="0.0.0.0", access_log=None),
    ]


def test_app_run_default_port(web_run_app_mock, aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, specification_dir=aiohttp_api_spec_dir, debug=True)
    app.run()
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5000, host="0.0.0.0", access_log=None),
    ]


def test_app_run_debug(web_run_app_mock, aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir)
    app.add_api("swagger_simple.yaml")
    app.run(debug=True)
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host="0.0.0.0", access_log=None),
    ]


def test_app_run_access_log(web_run_app_mock, aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir, debug=True)
    logger = logging.getLogger("especifico.aiohttp_app")
    app.run(access_log=logger)
    assert web_run_app_mock.call_args_list == [
        mock.call(app.app, port=5001, host="0.0.0.0", access_log=logger),
    ]


def test_app_run_server_error(web_run_app_mock, aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir)

    with pytest.raises(Exception) as exc_info:
        app.run(server="other")

    assert exc_info.value.args == ("Server other not recognized",)


def test_app_get_root_path_return_Path(aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir)
    assert isinstance(app.get_root_path(), pathlib.Path)


def test_app_get_root_path_exists(aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir)
    assert app.get_root_path().exists()


def test_app_get_root_path(aiohttp_api_spec_dir):
    app = AioHttpApp(__name__, port=5001, specification_dir=aiohttp_api_spec_dir)
    root_path = app.get_root_path()
    assert str(root_path).endswith(os.path.join("tests", "aiohttp"))


def test_app_get_root_path_not_in_sys_modules(sys_modules_mock, aiohttp_api_spec_dir):
    app = AioHttpApp("especifico", port=5001, specification_dir=aiohttp_api_spec_dir)
    root_path = app.get_root_path()
    assert str(root_path).endswith(os.sep + "especifico")


def test_app_get_root_path_invalid(sys_modules_mock, aiohttp_api_spec_dir):
    with pytest.raises(RuntimeError) as exc_info:
        AioHttpApp("error__", port=5001, specification_dir=aiohttp_api_spec_dir)

    assert exc_info.value.args == ("Invalid import name 'error__'",)


def test_app_with_empty_base_path_error(aiohttp_api_spec_dir):
    spec_dir = ".." / aiohttp_api_spec_dir.relative_to(TEST_FOLDER)
    app = AioHttpApp(__name__, port=5001, specification_dir=spec_dir, debug=True)
    with pytest.raises(EspecificoException) as exc_info:
        app.add_api("swagger_empty_base_path.yaml")

    assert exc_info.value.args == (
        "aiohttp doesn't allow to set empty base_path ('/'), " "use non-empty instead, e.g /api",
    )


def test_app_with_empty_base_path_and_only_one_api(aiohttp_api_spec_dir):
    spec_dir = ".." / aiohttp_api_spec_dir.relative_to(TEST_FOLDER)
    app = AioHttpApp(
        __name__, port=5001, specification_dir=spec_dir, debug=True, only_one_api=True,
    )
    api = app.add_api("swagger_empty_base_path.yaml")
    assert api is app.app


def test_app_add_two_apis_error_with_only_one_api(aiohttp_api_spec_dir):
    spec_dir = ".." / aiohttp_api_spec_dir.relative_to(TEST_FOLDER)
    app = AioHttpApp(
        __name__, port=5001, specification_dir=spec_dir, debug=True, only_one_api=True,
    )
    app.add_api("swagger_empty_base_path.yaml")

    with pytest.raises(EspecificoException) as exc_info:
        app.add_api("swagger_empty_base_path.yaml")

    assert exc_info.value.args == (
        "an api was already added, "
        "create a new app with 'only_one_api=False' "
        "to add more than one api",
    )
