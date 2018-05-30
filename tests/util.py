import json
import logging
import pathlib

import pytest
from connexion.apis import FlaskApi
from connexion.apps import FlaskApp

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
def simple_app(simple_api_spec_dir):
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app.add_api('swagger.yaml', validate_responses=True)
    return app

@pytest.fixture
def simple_app3(simple_api_spec_dir):
    app = FlaskApp(__name__, 5001, simple_api_spec_dir, debug=True)
    app.add_api('openapi.yaml', validate_responses=True)
    return app

@pytest.fixture
def problem_app(problem_api_spec_dir):
    app = FlaskApp(__name__, 5001, problem_api_spec_dir, debug=True)
    app.add_api('swagger.yaml', validate_responses=True)
