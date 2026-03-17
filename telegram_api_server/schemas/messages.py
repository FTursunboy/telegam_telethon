from pydantic import BaseModel, Field, HttpUrl, field_validator


class _ParseModeMixin(BaseModel):
    parse_mode: str | None = None

    @field_validator("parse_mode")
    @classmethod
    def validate_parse_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in {"Markdown", "HTML"}:
            raise ValueError("parse_mode must be Markdown or HTML")
        return value


class SendMessageRequest(_ParseModeMixin):
    session_name: str
    peer: str
    message: str = Field(max_length=4096)
    reply_to_message_id: int | None = Field(default=None, ge=1)


class SendVoiceRequest(BaseModel):
    session_name: str
    peer: str
    voice_url: HttpUrl
    caption: str | None = Field(default=None, max_length=1024)
    reply_to_message_id: int | None = Field(default=None, ge=1)


class SendFileRequest(_ParseModeMixin):
    session_name: str
    peer: str
    file_url: HttpUrl
    caption: str | None = Field(default=None, max_length=1024)
    reply_to_message_id: int | None = Field(default=None, ge=1)


class SendReactionRequest(BaseModel):
    session_name: str
    peer: str
    message_id: int = Field(ge=1)
    reaction: str | None = Field(default=None, max_length=32)
    remove: bool | None = None


class EditMessageRequest(_ParseModeMixin):
    session_name: str
    peer: str
    message_id: int = Field(ge=1)
    message: str = Field(max_length=4096)
