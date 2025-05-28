from httpx import Response
from starlette.testclient import TestClient

detail = "detail"
greeting = "greeting"
message = "message"
prefixes = ["openapi", "swagger"]


def test_greeting_dave(client: TestClient):
    name = "dave"
    for prefix in prefixes:
        res: Response = client.post(
            f"/{prefix}/{greeting}/{name}", json={message: "hi"}
        )
        assert res.status_code == 200
        assert name in res.json()[greeting]


def test_greeting_crash(client: TestClient):
    crash = "crash"
    for prefix in prefixes:
        res: Response = client.post(f"/{prefix}/{greeting}/name", json={message: crash})
        assert res.status_code == 500
        assert crash in res.json()[detail]


def test_greeting_invalid(client: TestClient):
    for prefix in prefixes:
        # a body is required in the POST
        res: Response = client.post(
            f"/{prefix}/{greeting}/name", json={message: "invalid"}
        )
        assert res.status_code == 500
        assert "Response body does not conform" in res.json()[detail]
