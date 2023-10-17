import json

import pytest

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


@pytest.mark.parametrize("specs", SPECS)
def test_app_with_multiple_definition(
    multiple_yaml_same_basepath_dir, specs, app_class
):
    app = app_class(
        __name__,
        specification_dir=".."
        / multiple_yaml_same_basepath_dir.relative_to(TEST_FOLDER),
    )

    for spec in specs:
        print(spec)
        app.add_api(**spec)

    app_client = app.test_client()

    response = app_client.post("/v1.0/greeting/Igor")
    assert response.status_code == 200
    print(response.text)
    assert response.json()["greeting"] == "Hello Igor"

    response = app_client.get("/v1.0/bye/Musti")
    assert response.status_code == 200
    assert response.text == "Goodbye Musti"
