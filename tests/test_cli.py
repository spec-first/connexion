import contextlib
import io
import logging
from unittest.mock import MagicMock

import pytest
from connexion.cli import main
from connexion.exceptions import ResolverError
from connexion.options import SwaggerUIOptions

from conftest import FIXTURES_FOLDER

try:
    import importlib_metadata
except ImportError:
    import importlib.metadata as importlib_metadata


@pytest.fixture(scope="function")
def mock_app_run(app_class, monkeypatch):
    mocked_app = MagicMock(name="mocked_app", wraps=app_class(__name__))

    def mocked_run(*args, **kwargs):
        mocked_app.middleware._build_middleware_stack()

    mocked_app.run = MagicMock(name="mocked_app.run", side_effect=mocked_run)

    def get_mocked_app(*args, **kwargs):
        return mocked_app

    mocked_app_class = MagicMock(name="mocked_app_class", side_effect=get_mocked_app)

    def get_mocked_app_class(*args, **kwargs):
        return mocked_app_class

    monkeypatch.setattr(
        "connexion.cli.connexion.utils.get_function_from_name", get_mocked_app_class
    )
    return mocked_app_class


@pytest.fixture()
def mock_get_function_from_name(monkeypatch):
    get_function_from_name = MagicMock()
    monkeypatch.setattr(
        "connexion.cli.connexion.utils.get_function_from_name", get_function_from_name
    )
    return get_function_from_name


@pytest.fixture()
def expected_arguments():
    """
    Default values arguments used to call `connexion.App` by cli.
    """
    return {
        "swagger_ui_options": SwaggerUIOptions(
            swagger_ui_path="/ui",
            swagger_ui_template_dir=None,
        ),
        "auth_all_paths": False,
    }


@pytest.fixture()
def spec_file():
    return str(FIXTURES_FOLDER / "simple/swagger.yaml")


def test_print_version():

    output = io.StringIO()
    with pytest.raises(SystemExit) as e_info, contextlib.redirect_stdout(output):
        main(["--version"])

    assert e_info.value.code == 0
    assert f"Connexion {importlib_metadata.version('connexion')}" in output.getvalue()


def test_run_missing_spec():
    output = io.StringIO()
    with pytest.raises(SystemExit) as e_info, contextlib.redirect_stderr(output):
        main(["run"])

    assert e_info.value.code != 0
    assert "the following arguments are required: spec_file" in output.getvalue()


def test_run_simple_spec(mock_app_run, spec_file):
    main(["run", spec_file])

    app_instance = mock_app_run()
    app_instance.run.assert_called()


def test_run_spec_with_host(mock_app_run, spec_file):
    main(["run", spec_file, "--host", "custom.host"])

    app_instance = mock_app_run()
    app_instance.run.assert_called()


def test_run_no_options_all_default(mock_app_run, expected_arguments, spec_file):
    main(["run", spec_file])
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_console_ui_from(mock_app_run, expected_arguments, spec_file):
    user_path = "/some/path/here"
    main(["run", spec_file, "--swagger-ui-template-dir", user_path])

    expected_arguments["swagger_ui_options"].swagger_ui_template_dir = user_path
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_console_ui_url(mock_app_run, expected_arguments, spec_file):
    user_url = "/console_ui_test"
    main(["run", spec_file, "--swagger-ui-path", user_url])

    expected_arguments["swagger_ui_options"].swagger_ui_path = user_url
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_auth_all_paths(mock_app_run, expected_arguments, spec_file):
    main(["run", spec_file, "--auth-all-paths"])

    expected_arguments["auth_all_paths"] = True
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_in_very_verbose_mode(
    mock_app_run, expected_arguments, spec_file, monkeypatch
):
    logging_config = MagicMock(name="connexion.cli.logging.basicConfig")
    monkeypatch.setattr("connexion.cli.logging.basicConfig", logging_config)

    main(["run", spec_file, "-vv"])

    logging_config.assert_called_with(level=logging.DEBUG)

    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_in_verbose_mode(mock_app_run, expected_arguments, spec_file, monkeypatch):
    logging_config = MagicMock(name="connexion.cli.logging.basicConfig")
    monkeypatch.setattr("connexion.cli.logging.basicConfig", logging_config)

    main(["run", spec_file, "-v"])

    logging_config.assert_called_with(level=logging.INFO)

    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_base_path(mock_app_run, expected_arguments, spec_file):
    main(["run", spec_file, "--base-path", "/foo"])

    expected_arguments = dict(
        base_path="/foo",
        resolver_error=None,
        validate_responses=False,
        strict_validation=False,
    )
    app_instance = mock_app_run()
    app_instance.add_api.assert_called_with(spec_file, **expected_arguments)


def test_run_unimplemented_operations(mock_app_run):
    spec_file = str(FIXTURES_FOLDER / "missing_implementation/swagger.yaml")
    with pytest.raises(ResolverError):
        main(["run", spec_file])

    spec_file = str(FIXTURES_FOLDER / "module_does_not_exist/swagger.yaml")
    with pytest.raises(ResolverError):
        main(["run", spec_file])


def test_run_unimplemented_operations_with_stub1(mock_app_run):
    spec_file = str(FIXTURES_FOLDER / "missing_implementation/swagger.yaml")
    main(["run", spec_file, "--stub"])


def test_run_unimplemented_operations_with_stub2(mock_app_run):
    spec_file = str(FIXTURES_FOLDER / "module_does_not_exist/swagger.yaml")
    main(["run", spec_file, "--stub"])


def test_run_unimplemented_operations_and_mock(mock_app_run):
    spec_file = str(FIXTURES_FOLDER / "missing_implementation/swagger.yaml")
    main(["run", spec_file, "--mock=all"])
