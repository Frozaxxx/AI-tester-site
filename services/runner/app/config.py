from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="RUNNER_", extra="ignore")

    runs_grpc_address: str
    projects_grpc_address: str
    allow_internal_urls: bool
    poll_interval_seconds: float


settings = Settings()
