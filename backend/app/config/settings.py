from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_connection_string: str = Field(min_length=1)
    mongodb_database_name: str = Field(min_length=1)
    cors_origins: list[str] = []
    environment: str = "development"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

