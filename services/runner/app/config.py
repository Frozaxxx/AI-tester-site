from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="RUNNER_", extra="ignore")

    runs_grpc_address: str
    projects_grpc_address: str
    rabbitmq_url: str
    allow_internal_urls: bool
    poll_interval_seconds: float
    llm_provider: Literal["gigachat", "openrouter"] = "gigachat"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    gigachat_credentials: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2-Max"
    gigachat_ca_bundle_file: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    s3_bucket: str = Field(default="", validation_alias="S3_BUCKET")
    s3_endpoint_url: str | None = Field(default=None, validation_alias="S3_ENDPOINT_URL")
    s3_access_key: str | None = Field(default=None, validation_alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, validation_alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", validation_alias="S3_REGION")
    s3_create_bucket: bool = Field(default=False, validation_alias="S3_CREATE_BUCKET")


settings = Settings()
