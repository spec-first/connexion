import json

import pytest
from connexion import App

from conftest import TEST_FOLDER

SPECS = [
    pytest.param(
        [
            {"specification": "swagger_greeting.yaml", "name": "greeting"},
            {"specification": "swagger_bye.yaml", "name": "bye"},
        ],
        id="swagger",
    ),
    pytest.param(
        [
            {"specification": "openapi_greeting.yaml", "name": "greeting"},
            {"specification": "openapi_bye.yaml", "name": "bye"},
        ],
        id="openapi",
    ),
]


@pytest.mark.parametrize("spec", SPECS)
def test_app_with_multiple_definition(multiple_yaml_same_basepath_dir, spec):
    # Create the app with a relative path and run the test_app testcase below.
    app = App(
        __name__,
        port=5001,
        specification_dir=".."
        / multiple_yaml_same_basepath_dir.relative_to(TEST_FOLDER),
        debug=True,
    )

    for s in spec:
        app.add_api(**s)

    app_client = app.app.test_client()

    post_greeting = app_client.post("/v1.0/greeting/jsantos")  # type: flask.Response
    assert post_greeting.status_code == 200
    greeting_response = json.loads(post_greeting.data.decode("utf-8"))
    assert greeting_response["greeting"] == "Hello jsantos"

    get_bye = app_client.get("/v1.0/bye/jsantos")  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b"Goodbye jsantos"
