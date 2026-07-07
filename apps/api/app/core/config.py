"""Configuration applicative de l'API Life Pilot."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres chargés depuis l'environnement."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Life Pilot API"
    api_prefix: str = ""
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+asyncpg://lifepilot:lifepilot@localhost:5432/lifepilot",
        validation_alias="DATABASE_URL",
    )
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance de configuration mise en cache."""

    return Settings()
