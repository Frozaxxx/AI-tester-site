from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="GATEWAY_", extra="ignore")

    auth_grpc_address: str
    projects_grpc_address: str
    runs_grpc_address: str
    redis_url: str
    cookie_secure: bool
    jwt_algorithm: str = Field(validation_alias="JWT_ALGORITHM")
    jwt_issuer: str = Field(validation_alias="JWT_ISSUER")
    jwt_audience: str = Field(validation_alias="JWT_AUDIENCE")


settings = Settings()
