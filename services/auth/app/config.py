from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="AUTH_", extra="ignore")

    database_url: str
    redis_url: str
    jwt_private_key: str
    jwt_algorithm: str = Field(validation_alias="JWT_ALGORITHM")
    jwt_issuer: str = Field(validation_alias="JWT_ISSUER")
    jwt_audience: str = Field(validation_alias="JWT_AUDIENCE")
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int
    grpc_host: str
    grpc_port: int
    login_attempts_limit: int
    login_block_minutes: int


settings = Settings()
