from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str  # matches DATABASE_URL in .env (case doesn't matter)


@lru_cache
def get_settings() -> Settings:
    return Settings()
