import json
import logging
import pathlib

import pytest
from connexion import FlaskApi
from connexion import FlaskApp

logging.basicConfig(level=logging.DEBUG)

TEST_FOLDER = pathlib.Path(__file__).parent
FIXTURES_FOLDER = TEST_FOLDER / 'fixtures'
SPEC_FOLDER = TEST_FOLDER / "fakeapi"


class FakeResponse(object):
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: ste
        """
        self.status_code = status_code
        self.text = text
        self.ok = status_code == 200

    def json(self):
        return json.loads(self.text)


# Helper fixtures functions
# =========================


@pytest.fixture
def oauth_requests(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        """
        :type url: str
        :type params: dict| None
        """
        params = params or {}
        if url == "https://oauth.example/token_info":
            token = params['access_token']
            if token in ["100", "has_myscope"]:
                return FakeResponse(200, '{"uid": "test-user", "scope": ["myscope"]}')
            if token in ["200", "has_wrongscope"]:
                return FakeResponse(200, '{"uid": "test-user", "scope": ["wrongscope"]}')
            if token == "has_myscope_otherscope":
                return FakeResponse(200, '{"uid": "test-user", "scope": ["myscope", "otherscope"]}')
            if token in ["300", "is_not_invalid"]:
                return FakeResponse(404, '')
        return url

    monkeypatch.setattr('connexion.decorators.security.session.get', fake_get)


@pytest.fixture
def app():
    app = FlaskApp(__name__, 5001, SPEC_FOLDER, debug=True)
    app.add_api('api.yaml', validate_responses=True)
    return app


@pytest.fixture
def simple_api_spec_dir():
    return FIXTURES_FOLDER / 'simple'


@pytest.fixture
def problem_api_spec_dir():
    return FIXTURES_FOLDER / 'problem'


@pytest.fixture
def secure_api_spec_dir():
    return FIXTURES_FOLDER / 'secure_api'


@pytest.fixture
def default_param_error_spec_dir():
    return FIXTURES_FOLDER / 'default_param_error'


def build_app_from_fixture(api_spec_folder, **kwargs):
    debug = True
    if 'debug' in kwargs:
        debug = kwargs['debug']
        del(kwargs['debug'])
    app = FlaskApp(__name__, 5001, FIXTURES_FOLDER / api_spec_folder, debug=debug)
    app.add_api('swagger.yaml', **kwargs)
    return app


@pytest.fixture(scope="session")
def simple_app():
    return build_app_from_fixture('simple', validate_responses=True)


@pytest.fixture(scope="session")
def snake_case_app():
    return build_app_from_fixture('snake_case', validate_responses=True, pythonic_params=True)


@pytest.fixture(scope="session")
def invalid_resp_allowed_app():
    return build_app_from_fixture('simple', validate_responses=False)


@pytest.fixture(scope="session")
def strict_app():
    return build_app_from_fixture('simple', validate_responses=True, strict_validation=True)


@pytest.fixture(scope="session")
def problem_app():
    return build_app_from_fixture('problem', validate_responses=True)


@pytest.fixture(scope="session")
def schema_app():
    return build_app_from_fixture('different_schemas', validate_responses=True)


@pytest.fixture(scope="session")
def secure_endpoint_app():
    return build_app_from_fixture('secure_endpoint', validate_responses=True)


@pytest.fixture(scope="session")
def secure_api_app():
    return build_app_from_fixture('secure_api')


@pytest.fixture(scope="session")
def unordered_definition_app():
    return build_app_from_fixture('unordered_definition')


@pytest.fixture(scope="session")
def bad_operations_app():
    return build_app_from_fixture('bad_operations', resolver_error=501)
