"""Настройки сервиса. Значения берутся из файла .env в корне проекта."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env лежит в корне проекта: services/<сервис>/app/config.py -> три уровня вверх
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="RUNS_", extra="ignore")

    database_url: str


settings = Settings()
