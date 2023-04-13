import logging
from unittest.mock import MagicMock

import connexion
import importlib_metadata
import pytest
from click.testing import CliRunner
from connexion.cli import main
from connexion.exceptions import ResolverError

from conftest import FIXTURES_FOLDER


@pytest.fixture()
def mock_app_run(mock_get_function_from_name):
    test_server = MagicMock(wraps=connexion.FlaskApp(__name__))
    test_server.run = MagicMock(return_value=True)
    test_app = MagicMock(return_value=test_server)
    mock_get_function_from_name.return_value = test_app
    return test_app


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
        "swagger_ui_options": {
            "serve_spec": True,
            "swagger_ui": True,
            "swagger_path": None,
            "swagger_url": None,
        },
        "auth_all_paths": False,
    }


@pytest.fixture()
def spec_file():
    return str(FIXTURES_FOLDER / "simple/swagger.yaml")


def test_print_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"], catch_exceptions=False)
    assert f"Connexion {importlib_metadata.version('connexion')}" in result.output


def test_run_missing_spec():
    runner = CliRunner()
    result = runner.invoke(main, ["run"], catch_exceptions=False)
    assert "Missing argument" in result.output


def test_run_simple_spec(mock_app_run, spec_file):
    runner = CliRunner()
    runner.invoke(main, ["run", spec_file], catch_exceptions=False)

    app_instance = mock_app_run()
    app_instance.run.assert_called()


def test_run_spec_with_host(mock_app_run, spec_file):
    runner = CliRunner()
    runner.invoke(
        main, ["run", spec_file, "--host", "custom.host"], catch_exceptions=False
    )

    app_instance = mock_app_run()
    app_instance.run.assert_called()


def test_run_no_options_all_default(mock_app_run, expected_arguments, spec_file):
    runner = CliRunner()
    runner.invoke(main, ["run", spec_file], catch_exceptions=False)
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_hide_spec(mock_app_run, expected_arguments, spec_file):
    runner = CliRunner()
    runner.invoke(main, ["run", spec_file, "--hide-spec"], catch_exceptions=False)

    expected_arguments["swagger_ui_options"]["serve_spec"] = False
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_hide_console_ui(mock_app_run, expected_arguments, spec_file):
    runner = CliRunner()
    runner.invoke(main, ["run", spec_file, "--hide-console-ui"], catch_exceptions=False)

    expected_arguments["swagger_ui_options"]["swagger_ui"] = False
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_console_ui_from(mock_app_run, expected_arguments, spec_file):
    user_path = "/some/path/here"
    runner = CliRunner()
    runner.invoke(
        main, ["run", spec_file, "--console-ui-from", user_path], catch_exceptions=False
    )

    expected_arguments["swagger_ui_options"]["swagger_path"] = user_path
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_console_ui_url(mock_app_run, expected_arguments, spec_file):
    user_url = "/console_ui_test"
    runner = CliRunner()
    runner.invoke(
        main, ["run", spec_file, "--console-ui-url", user_url], catch_exceptions=False
    )

    expected_arguments["swagger_ui_options"]["swagger_url"] = user_url
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_auth_all_paths(mock_app_run, expected_arguments, spec_file):
    runner = CliRunner()
    runner.invoke(main, ["run", spec_file, "--auth-all-paths"], catch_exceptions=False)

    expected_arguments["auth_all_paths"] = True
    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_in_very_verbose_mode(
    mock_app_run, expected_arguments, spec_file, monkeypatch
):
    logging_config = MagicMock(name="connexion.cli.logging.basicConfig")
    monkeypatch.setattr("connexion.cli.logging.basicConfig", logging_config)

    runner = CliRunner()
    runner.invoke(main, ["run", spec_file, "-vv"], catch_exceptions=False)

    logging_config.assert_called_with(level=logging.DEBUG)

    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_in_verbose_mode(mock_app_run, expected_arguments, spec_file, monkeypatch):
    logging_config = MagicMock(name="connexion.cli.logging.basicConfig")
    monkeypatch.setattr("connexion.cli.logging.basicConfig", logging_config)

    runner = CliRunner()
    runner.invoke(main, ["run", spec_file, "-v"], catch_exceptions=False)

    logging_config.assert_called_with(level=logging.INFO)

    mock_app_run.assert_called_with("connexion.cli", **expected_arguments)


def test_run_using_option_base_path(mock_app_run, expected_arguments, spec_file):
    runner = CliRunner()
    runner.invoke(
        main, ["run", spec_file, "--base-path", "/foo"], catch_exceptions=False
    )

    expected_arguments = dict(
        base_path="/foo",
        resolver_error=None,
        validate_responses=False,
        strict_validation=False,
    )
    mock_app_run().add_api.assert_called_with(spec_file, **expected_arguments)


def test_run_unimplemented_operations_and_stub(mock_app_run):
    runner = CliRunner()

    spec_file = str(FIXTURES_FOLDER / "missing_implementation/swagger.yaml")
    with pytest.raises(ResolverError):
        runner.invoke(main, ["run", spec_file], catch_exceptions=False)
    # yet can be run with --stub option
    result = runner.invoke(main, ["run", spec_file, "--stub"], catch_exceptions=False)
    assert result.exit_code == 0

    spec_file = str(FIXTURES_FOLDER / "module_does_not_exist/swagger.yaml")
    with pytest.raises(ResolverError):
        runner.invoke(main, ["run", spec_file], catch_exceptions=False)
    # yet can be run with --stub option
    result = runner.invoke(main, ["run", spec_file, "--stub"], catch_exceptions=False)
    assert result.exit_code == 0


def test_run_unimplemented_operations_and_mock(mock_app_run):
    runner = CliRunner()

    spec_file = str(FIXTURES_FOLDER / "missing_implementation/swagger.yaml")
    with pytest.raises(ResolverError):
        runner.invoke(main, ["run", spec_file], catch_exceptions=False)
    # yet can be run with --mock option
    result = runner.invoke(
        main, ["run", spec_file, "--mock=all"], catch_exceptions=False
    )
    assert result.exit_code == 0
