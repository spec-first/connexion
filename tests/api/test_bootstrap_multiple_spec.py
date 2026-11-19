import json

import pytest
from connexion import AsyncApp

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


def test_app_with_prefix_basepath():
    app = AsyncApp(
        __name__,
        specification_dir=TEST_FOLDER / "fixtures" / "multiple_yaml_prefix_basepath",
    )
    # Register the narrower base path first. The broader one must not shadow it.
    app.add_api(specification="openapi_path1.yaml")
    app.add_api(specification="openapi_root.yaml")
    app_client = app.test_client()

    assert app_client.get("/path1/endpoint2").status_code == 200
    assert app_client.get("/endpoint1").status_code == 200
