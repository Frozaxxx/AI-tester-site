from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="PROJECTS_", extra="ignore")

    database_url: str
    grpc_host: str
    grpc_port: int


settings = Settings()
