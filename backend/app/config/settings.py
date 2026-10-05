from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_connection_string: str = Field(min_length=1)
    mongodb_database_name: str = Field(min_length=1)
    cors_origins: list[str] = []
    environment: str = "development"
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90)
    google_web_client_id: str | None = None
    auth_rate_limit_per_minute: int = Field(default=10, ge=1)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
