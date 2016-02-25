import pathlib
import json
import logging
import pytest

from connexion.app import App

logging.basicConfig(level=logging.DEBUG)

TEST_FOLDER = pathlib.Path(__file__).parent
FIXTURES_FOLDER = TEST_FOLDER / 'fixtures'
SPEC_FOLDER = TEST_FOLDER / "fakeapi"


class FakeResponse:
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
        if url == "https://ouath.example/token_info":
            token = params['access_token']
            if token == "100":
                return FakeResponse(200, '{"uid": "test-user", "scope": ["myscope"]}')
            if token == "200":
                return FakeResponse(200, '{"uid": "test-user", "scope": ["wrongscope"]}')
            if token == "300":
                return FakeResponse(404, '')
        return url

    monkeypatch.setattr('connexion.decorators.security.session.get', fake_get)


@pytest.fixture
def app():
    app = App(__name__, 5001, SPEC_FOLDER, debug=True)
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


def build_app_from_fixture(api_spec_folder):
    app = App(__name__, 5001, FIXTURES_FOLDER / api_spec_folder, debug=True)
    app.add_api('swagger.yaml', validate_responses=True)
    return app


@pytest.fixture
def simple_app():
    return build_app_from_fixture('simple')


@pytest.fixture
def problem_app():
    return build_app_from_fixture('problem')


@pytest.fixture
def schema_app():
    return build_app_from_fixture('different_schemas')


@pytest.fixture
def secure_endpoint_app():
    return build_app_from_fixture('secure_endpoint')


@pytest.fixture
def secure_api_app():
    return build_app_from_fixture('secure_api')
