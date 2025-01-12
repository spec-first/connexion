from hello import app
from httpx import Response
from pytest_mock import MockerFixture
from starlette.testclient import TestClient

greeting = "greeting"
prefixes = ["openapi", "swagger"]


def test_greeting_success(client: TestClient):
    name = "dave"
    for prefix in prefixes:
        # a body is required in the POST
        res: Response = client.post(
            f"/{prefix}/{greeting}/{name}", json={"message": "hi"}
        )
        assert res.status_code == 200
        assert name in res.json()[greeting]


def test_greeting_exception(client: TestClient):
    name = "dave"
    for prefix in prefixes:
        # a body is required in the POST
        res: Response = client.post(
            f"/{prefix}/{greeting}/{name}", json={"message": "crash"}
        )
        assert res.status_code == 500
        assert name in res.json()["detail"]


def test_greeting_invalid(client: TestClient):
    name = "dave"
    for prefix in prefixes:
        # a body is required in the POST
        res: Response = client.post(
            f"/{prefix}/{greeting}/{name}", json={"message": "invalid"}
        )
        assert res.status_code == 500
        assert "Response body does not conform" in res.json()["detail"]


def test_main(mocker: MockerFixture):
    # patch the run-app function to do nothing
    mock_run = mocker.patch("hello.app.conn_app.run")
    app.main()
    mock_run.assert_called()
