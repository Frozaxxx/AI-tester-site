"""Настройки сервиса. Значения берутся из файла .env в корне проекта."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", env_prefix="AUTH_", extra="ignore")

    database_url: str
    redis_url: str
    jwt_private_key_path: str  # RSA-ключ, которым подписываем JWT
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 1


settings = Settings()
