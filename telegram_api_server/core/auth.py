from typing import Any

from fastapi import HTTPException, Request, status

from telegram_api_server.core.config import get_settings


def extract_api_key(request: Request, body: Any | None) -> str | None:
    key = request.headers.get("X-API-Key")
    if key:
        return key
    if isinstance(body, dict) and body.get("api_key"):
        return str(body["api_key"])
    query_key = request.query_params.get("api_key")
    if query_key:
        return query_key
    return None


def ensure_authorized(request: Request, body: Any | None = None) -> None:
    key = extract_api_key(request, body)
    if not key or key != get_settings().app_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "Invalid or missing API key"},
        )
