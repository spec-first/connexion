import logging

from click.testing import CliRunner

import pytest
from conftest import FIXTURES_FOLDER
from connexion import App
from connexion.cli import main
from mock import MagicMock


@pytest.fixture()
def mock_app_run(monkeypatch):
    test_server = MagicMock(wraps=App(__name__))
    test_server.run = MagicMock(return_value=True)
    test_app = MagicMock(return_value=test_server)
    monkeypatch.setattr('connexion.cli.App', test_app)
    return test_server


def test_run_missing_spec():
    runner = CliRunner()
    result = runner.invoke(main, ['run'], catch_exceptions=False)
    assert "Missing argument" in result.output


def test_run_simple_spec(mock_app_run):
    spec_file = str(FIXTURES_FOLDER / 'simple/swagger.yaml')
    default_port = 5000
    runner = CliRunner()
    runner.invoke(main, ['run', spec_file], catch_exceptions=False)

    mock_app_run.run.assert_called_with(port=default_port, server=None)


def test_run_in_debug_mode(mock_app_run, monkeypatch):
    spec_file = str(FIXTURES_FOLDER / 'simple/swagger.yaml')

    logging_config = MagicMock(name='connexion.cli.logging.basicConfig')
    monkeypatch.setattr('connexion.cli.logging.basicConfig',
                        logging_config)

    runner = CliRunner()
    runner.invoke(main, ['run', spec_file, '-d'], catch_exceptions=False)

    logging_config.assert_called_with(level=logging.DEBUG)
