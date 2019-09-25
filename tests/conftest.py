import json
import logging
import pathlib
import sys

import pytest

from connexion import App

logging.basicConfig(level=logging.DEBUG)

TEST_FOLDER = pathlib.Path(__file__).parent
FIXTURES_FOLDER = TEST_FOLDER / 'fixtures'
SPEC_FOLDER = TEST_FOLDER / "fakeapi"
SPECS = ["swagger.yaml", "openapi.yaml"]
OPENAPI_SPEC_ONLY = ["openapi.yaml"]


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
    def fake_get(url, params=None, headers=None, timeout=None):
        """
        :type url: str
        :type params: dict| None
        """
        headers = headers or {}
        if url == "https://oauth.example/token_info":
            token = headers.get('Authorization', 'invalid').split()[-1]
            if token in ["100", "has_myscope"]:
                return FakeResponse(200, '{"uid": "test-user", "scope": ["myscope"]}')
            if token in ["200", "has_wrongscope"]:
                return FakeResponse(200, '{"uid": "test-user", "scope": ["wrongscope"]}')
            if token == "has_myscope_otherscope":
                return FakeResponse(200, '{"uid": "test-user", "scope": ["myscope", "otherscope"]}')
            if token in ["300", "is_not_invalid"]:
                return FakeResponse(404, '')
            if token == "has_scopes_in_scopes_with_s":
                return FakeResponse(200, '{"uid": "test-user", "scopes": ["myscope", "otherscope"]}')
        return url

    monkeypatch.setattr('connexion.decorators.security.session.get', fake_get)


@pytest.fixture
def app():
    cnx_app = App(__name__, port=5001, specification_dir=SPEC_FOLDER, debug=True)
    cnx_app.add_api('api.yaml', validate_responses=True)
    return cnx_app


@pytest.fixture
def simple_api_spec_dir():
    return FIXTURES_FOLDER / 'simple'


@pytest.fixture
def aiohttp_api_spec_dir():
    return FIXTURES_FOLDER / 'aiohttp'


@pytest.fixture
def problem_api_spec_dir():
    return FIXTURES_FOLDER / 'problem'


@pytest.fixture
def secure_api_spec_dir():
    return FIXTURES_FOLDER / 'secure_api'


@pytest.fixture
def default_param_error_spec_dir():
    return FIXTURES_FOLDER / 'default_param_error'


@pytest.fixture
def json_validation_spec_dir():
    return FIXTURES_FOLDER / 'json_validation'


def build_app_from_fixture(api_spec_folder, spec_file='openapi.yaml', **kwargs):
    debug = True
    if 'debug' in kwargs:
        debug = kwargs['debug']
        del (kwargs['debug'])

    cnx_app = App(__name__,
                  port=5001,
                  specification_dir=FIXTURES_FOLDER / api_spec_folder,
                  debug=debug)

    cnx_app.add_api(spec_file, **kwargs)
    cnx_app._spec_file = spec_file
    return cnx_app


@pytest.fixture(scope="session", params=SPECS)
def simple_app(request):
    return build_app_from_fixture('simple', request.param, validate_responses=True)


@pytest.fixture(scope="session", params=OPENAPI_SPEC_ONLY)
def simple_openapi_app(request):
    return build_app_from_fixture('simple', request.param, validate_responses=True)


@pytest.fixture(scope="session", params=SPECS)
def snake_case_app(request):
    return build_app_from_fixture('snake_case', request.param,
                                  validate_responses=True,
                                  pythonic_params=True)


@pytest.fixture(scope="session", params=SPECS)
def invalid_resp_allowed_app(request):
    return build_app_from_fixture('simple', request.param,
                                  validate_responses=False)


@pytest.fixture(scope="session", params=SPECS)
def strict_app(request):
    return build_app_from_fixture('simple', request.param,
                                  validate_responses=True,
                                  strict_validation=True)


@pytest.fixture(scope="session", params=SPECS)
def problem_app(request):
    return build_app_from_fixture('problem', request.param,
                                  validate_responses=True)


@pytest.fixture(scope="session", params=SPECS)
def schema_app(request):
    return build_app_from_fixture('different_schemas', request.param,
                                  validate_responses=True)


@pytest.fixture(scope="session", params=SPECS)
def secure_endpoint_app(request):
    return build_app_from_fixture('secure_endpoint', request.param,
                                  validate_responses=True, pass_context_arg_name='req_context')


@pytest.fixture(scope="session", params=SPECS)
def secure_api_app(request):
    options = {"swagger_ui": False}
    return build_app_from_fixture('secure_api', request.param,
                                  options=options, auth_all_paths=True)


@pytest.fixture(scope="session", params=SPECS)
def unordered_definition_app(request):
    return build_app_from_fixture('unordered_definition', request.param)


@pytest.fixture(scope="session", params=SPECS)
def bad_operations_app(request):
    return build_app_from_fixture('bad_operations', request.param,
                                  resolver_error=501)


@pytest.fixture(scope="session", params=SPECS)
def query_sanitazion(request):
    return build_app_from_fixture('query_sanitazion', request.param)


if sys.version_info < (3, 5, 3) and sys.version_info[0] == 3:
    @pytest.fixture
    def aiohttp_client(test_client):
        return test_client
