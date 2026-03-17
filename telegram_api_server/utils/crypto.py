import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from telegram_api_server.core.config import get_settings


def _build_fernet() -> Fernet:
    raw_key = get_settings().encryption_key
    if not raw_key:
        key = base64.urlsafe_b64encode(hashlib.sha256(b"dev-default-key").digest())
        return Fernet(key)
    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        return Fernet(key)


def encrypt_text(value: str | None) -> str | None:
    if not value:
        return value
    return _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
