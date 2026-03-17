from pydantic import BaseModel, Field, HttpUrl, field_validator


class StartLoginRequest(BaseModel):
    api_id: str
    api_hash: str = Field(min_length=32)
    type: str
    phone: str | None = None
    bot_token: str | None = None
    session_name: str | None = None
    webhook_url: HttpUrl
    force_recreate: bool | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in {"user", "bot"}:
            raise ValueError("type must be user or bot")
        return value


class CompleteCodeRequest(BaseModel):
    session_name: str
    code: str = Field(min_length=5, max_length=6)


class Complete2FARequest(BaseModel):
    session_name: str
    password: str


class SessionRequest(BaseModel):
    session_name: str
    remove_container: bool | None = None
