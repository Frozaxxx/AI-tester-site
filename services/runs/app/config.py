"""Настройки сервиса. Значения берутся из файла .env в корне проекта."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", env_prefix="RUNS_", extra="ignore")

    database_url: str


settings = Settings()
