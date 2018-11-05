import logging

from click.testing import CliRunner

import connexion
import pytest
from conftest import FIXTURES_FOLDER
from connexion.cli import main
from connexion.exceptions import ResolverError
from mock import MagicMock
from mock import call as mock_call


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
        'connexion.cli.connexion.utils.get_function_from_name',
        get_function_from_name
    )
    return get_function_from_name


@pytest.fixture()
def expected_arguments():
    """
    Default values arguments used to call `connexion.App` by cli.
    """
    return {
        "options": {
            "swagger_json": True,
            "swagger_ui": True,
            "swagger_path": None,
            "swagger_url": None,
        },
        "auth_all_paths": False,
        "debug": False
    }


@pytest.fixture()
def spec_file():
    return str(FIXTURES_FOLDER / 'simple/swagger.yaml')


def test_print_version():
    runner = CliRunner()
    result = runner.invoke(main, ['--version'], catch_exceptions=False)
    assert "Connexion {}".format(connexion.__version__) in result.output


def test_run_missing_spec():
    runner = CliRunner()
    result = runner.invoke(main, ['run'], catch_exceptions=False)
    assert "Missing argument" in result.output


def test_run_simple_spec(mock_app_run, spec_file):
    default_port = 5000
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file], catch_exceptions=False)

    app_instance = mock_app_run()
    app_instance.run.assert_called_with(
        port=default_port,
        host=None,
        server='flask',
        debug=False)


def test_run_spec_with_host(mock_app_run, spec_file):
    default_port = 5000
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--host', 'custom.host'], catch_exceptions=False)

    app_instance = mock_app_run()
    app_instance.run.assert_called_with(
        port=default_port,
        host='custom.host',
        server='flask',
        debug=False)


def test_run_no_options_all_default(mock_app_run, expected_arguments, spec_file):
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file], catch_exceptions=False)
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_using_option_hide_spec(mock_app_run, expected_arguments,
                                           spec_file):
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--hide-spec'],
                  catch_exceptions=False)

    expected_arguments['options']['swagger_json'] = False
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_using_option_hide_console_ui(mock_app_run, expected_arguments,
                                                 spec_file):
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--hide-console-ui'],
                  catch_exceptions=False)

    expected_arguments['options']['swagger_ui'] = False
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_using_option_console_ui_from(mock_app_run, expected_arguments,
                                           spec_file):
    user_path = '/some/path/here'
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--console-ui-from', user_path],
                  catch_exceptions=False)

    expected_arguments['options']['swagger_path'] = user_path
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_using_option_console_ui_url(mock_app_run, expected_arguments,
                                           spec_file):
    user_url = '/console_ui_test'
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--console-ui-url', user_url],
                  catch_exceptions=False)

    expected_arguments['options']['swagger_url'] = user_url
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_using_option_auth_all_paths(mock_app_run, expected_arguments,
                                                 spec_file):
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--auth-all-paths'],
                  catch_exceptions=False)

    expected_arguments['auth_all_paths'] = True
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_in_debug_mode(mock_app_run, expected_arguments, spec_file,
                           monkeypatch):
    logging_config = MagicMock(name='connexion.cli.logging.basicConfig')
    monkeypatch.setattr('connexion.cli.logging.basicConfig',
                        logging_config)

    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '-d'], catch_exceptions=False)

    logging_config.assert_called_with(level=logging.DEBUG)

    expected_arguments['debug'] = True
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_in_very_verbose_mode(mock_app_run, expected_arguments, spec_file,
                           monkeypatch):
    logging_config = MagicMock(name='connexion.cli.logging.basicConfig')
    monkeypatch.setattr('connexion.cli.logging.basicConfig',
                        logging_config)

    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '-vv'], catch_exceptions=False)

    logging_config.assert_called_with(level=logging.DEBUG)

    expected_arguments['debug'] = True
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_in_verbose_mode(mock_app_run, expected_arguments, spec_file,
                           monkeypatch):
    logging_config = MagicMock(name='connexion.cli.logging.basicConfig')
    monkeypatch.setattr('connexion.cli.logging.basicConfig',
                        logging_config)

    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '-v'], catch_exceptions=False)

    logging_config.assert_called_with(level=logging.INFO)

    expected_arguments['debug'] = False
    mock_app_run.assert_called_with('connexion.cli', **expected_arguments)


def test_run_using_option_base_path(mock_app_run, expected_arguments,
                                    spec_file):
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '--base-path', '/foo'],
                  catch_exceptions=False)

    expected_arguments = dict(base_path='/foo',
                              resolver_error=None,
                              validate_responses=False,
                              strict_validation=False)
    mock_app_run().add_api.assert_called_with(spec_file, **expected_arguments)


def test_run_unimplemented_operations_and_stub(mock_app_run):
    runner = CliRunner()

    spec_file = str(FIXTURES_FOLDER / 'missing_implementation/swagger.yaml')
    with pytest.raises(AttributeError):
        runner.invoke(main, ['run', spec_file], catch_exceptions=False)
    # yet can be run with --stub option
    result = runner.invoke(main, ['run', spec_file, '--stub'], catch_exceptions=False)
    assert result.exit_code == 0

    spec_file = str(FIXTURES_FOLDER / 'module_does_not_exist/swagger.yaml')
    with pytest.raises(ImportError):
        runner.invoke(main, ['run', spec_file], catch_exceptions=False)
    # yet can be run with --stub option
    result = runner.invoke(main, ['run', spec_file, '--stub'], catch_exceptions=False)
    assert result.exit_code == 0


def test_run_unimplemented_operations_and_mock(mock_app_run):
    runner = CliRunner()

    spec_file = str(FIXTURES_FOLDER / 'missing_implementation/swagger.yaml')
    with pytest.raises(AttributeError):
        runner.invoke(main, ['run', spec_file], catch_exceptions=False)
    # yet can be run with --mock option
    result = runner.invoke(main, ['run', spec_file, '--mock=all'], catch_exceptions=False)
    assert result.exit_code == 0


def test_run_with_wsgi_containers(mock_app_run, spec_file):
    runner = CliRunner()

    # missing gevent
    result = runner.invoke(main,
                           ['run', spec_file, '-w', 'gevent'],
                           catch_exceptions=False)
    assert 'gevent library is not installed' in result.output
    assert result.exit_code == 1

    # missing tornado
    result = runner.invoke(main,
                           ['run', spec_file, '-w', 'tornado'],
                           catch_exceptions=False)
    assert 'tornado library is not installed' in result.output
    assert result.exit_code == 1

    # using flask
    result = runner.invoke(main,
                           ['run', spec_file, '-w', 'flask'],
                           catch_exceptions=False)
    assert result.exit_code == 0


def test_run_with_aiohttp_not_installed(mock_app_run, spec_file):
    import sys
    aiohttp_bkp = sys.modules.pop('aiohttp', None)

    runner = CliRunner()

    # missing aiohttp
    result = runner.invoke(main,
                           ['run', spec_file, '-f', 'aiohttp'],
                           catch_exceptions=False)
    sys.modules['aiohttp'] = aiohttp_bkp

    assert 'aiohttp library is not installed' in result.output
    assert result.exit_code == 1


def test_run_with_wsgi_server_and_server_opts(mock_app_run, spec_file):
    runner = CliRunner()

    result = runner.invoke(main,
                           ['run', spec_file,
                            '-w', 'flask',
                            '-s', 'flask'],
                           catch_exceptions=False)
    assert "these options are mutually exclusive" in result.output
    assert result.exit_code == 2


def test_run_with_incompatible_server_and_default_framework(mock_app_run, spec_file):
    runner = CliRunner()

    result = runner.invoke(main,
                           ['run', spec_file,
                           '-s', 'aiohttp'],
                           catch_exceptions=False)
    assert "Invalid server 'aiohttp' for app-framework 'flask'" in result.output
    assert result.exit_code == 2


def test_run_with_incompatible_server_and_framework(mock_app_run, spec_file):
    runner = CliRunner()

    result = runner.invoke(main,
                           ['run', spec_file,
                           '-s', 'flask',
                           '-f', 'aiohttp'],
                           catch_exceptions=False)
    assert "Invalid server 'flask' for app-framework 'aiohttp'" in result.output
    assert result.exit_code == 2
