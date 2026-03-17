from fastapi.testclient import TestClient

from telegram_api_server.main import app


def test_coordinates_requires_valid_payload() -> None:
    client = TestClient(app)
    response = client.post("/api/hs/data/coordinates", json={"user_id": "u"})
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is False
    assert body["saved"] == 0
