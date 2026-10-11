"""Настройки сервиса. Значения берутся из файла .env в корне проекта."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env лежит в корне проекта: services/<сервис>/app/config.py -> три уровня вверх
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="AUTH_", extra="ignore")

    database_url: str
    redis_url: str
    jwt_private_key: str  # RSA-ключ в формате PEM, которым подписываем JWT
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 1


settings = Settings()
