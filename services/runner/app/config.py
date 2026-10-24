from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="RUNNER_", extra="ignore")

    runs_grpc_address: str
    projects_grpc_address: str
    allow_internal_urls: bool
    poll_interval_seconds: float
    llm_provider: Literal["gigachat", "openrouter", "none"] = "none"
    gigachat_credentials: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2-Max"
    gigachat_ca_bundle_file: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"


settings = Settings()
