from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    data: dict[str, Any]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


class UnauthorizedResponse(BaseModel):
    error: str = "Unauthorized"
    message: str = "Invalid or missing API key"


class SessionStatusData(BaseModel):
    session_name: str
    status: str
    type: str
    has_container: bool
    container_name: str | None
    container_port: int | None
    phone: str | None
    telegram_username: str | None
    first_name: str | None
    last_error: str | None
    created_at: datetime | None
    updated_at: datetime | None
