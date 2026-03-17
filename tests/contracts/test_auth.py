from fastapi.testclient import TestClient

from telegram_api_server.main import app


def test_invalid_api_key() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/session/status", json={"session_name": "x"})
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized", "message": "Invalid or missing API key"}
