from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_api_key: str = "change-me"

    database_url: str = "mysql+aiomysql://telegram:telegram@mysql:3306/telegram_api"

    encryption_key: str = ""
    telethon_session_dir: str = "/data/sessions"

    webhook_timeout_seconds: int = 5
    webhook_retry_attempts: int = 2
    webhook_dedup_ttl_seconds: int = 60
    webhook_max_pending_per_session: int = 200

    entity_cache_ttl_seconds: int = 300
    telegram_reconnect_base_seconds: int = 1
    telegram_reconnect_max_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
