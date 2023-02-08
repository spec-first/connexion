import logging
import pathlib

import pytest
from connexion import App
from connexion.resolver import MethodResolver, MethodViewResolver

logging.basicConfig(level=logging.INFO)

TEST_FOLDER = pathlib.Path(__file__).parent
FIXTURES_FOLDER = TEST_FOLDER / "fixtures"
SPEC_FOLDER = TEST_FOLDER / "fakeapi"
OPENAPI2_SPEC = "swagger.yaml"
OPENAPI3_SPEC = "openapi.yaml"
SPECS = [OPENAPI2_SPEC, OPENAPI3_SPEC]
METHOD_VIEW_RESOLVERS = [MethodResolver, MethodViewResolver]


@pytest.fixture
def simple_api_spec_dir():
    return FIXTURES_FOLDER / "simple"


@pytest.fixture
def problem_api_spec_dir():
    return FIXTURES_FOLDER / "problem"


@pytest.fixture
def secure_api_spec_dir():
    return FIXTURES_FOLDER / "secure_api"


@pytest.fixture
def default_param_error_spec_dir():
    return FIXTURES_FOLDER / "default_param_error"


@pytest.fixture
def json_validation_spec_dir():
    return FIXTURES_FOLDER / "json_validation"


@pytest.fixture(scope="session")
def json_datetime_dir():
    return FIXTURES_FOLDER / "datetime_support"


@pytest.fixture(scope="session", params=SPECS)
def spec(request):
    return request.param


@pytest.fixture(scope="session", params=METHOD_VIEW_RESOLVERS)
def method_view_resolver(request):
    return request.param


def build_app_from_fixture(
    api_spec_folder, spec_file="openapi.yaml", middlewares=None, **kwargs
):
    cnx_app = App(
        __name__,
        specification_dir=FIXTURES_FOLDER / api_spec_folder,
        middlewares=middlewares,
    )

    cnx_app.add_api(spec_file, **kwargs)
    cnx_app._spec_file = spec_file
    return cnx_app
