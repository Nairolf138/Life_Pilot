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
    refresh_token_expire_minutes: int = 60 * 24 * 14
    cors_origins: list[str] = Field(default_factory=list)
    storage_backend: str = Field(default="local", validation_alias="STORAGE_BACKEND")
    storage_local_root: str = Field(
        default="/tmp/lifepilot-documents",
        validation_alias="STORAGE_LOCAL_ROOT",
    )
    storage_s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias="STORAGE_S3_ENDPOINT_URL",
    )
    storage_s3_bucket: str = Field(
        default="lifepilot-documents",
        validation_alias="STORAGE_S3_BUCKET",
    )
    storage_s3_access_key: str | None = Field(
        default=None,
        validation_alias="STORAGE_S3_ACCESS_KEY",
    )
    storage_s3_secret_key: str | None = Field(
        default=None,
        validation_alias="STORAGE_S3_SECRET_KEY",
    )
    storage_s3_region: str = Field(
        default="us-east-1",
        validation_alias="STORAGE_S3_REGION",
    )
    storage_s3_use_ssl: bool = Field(
        default=True,
        validation_alias="STORAGE_S3_USE_SSL",
    )
    n8n_internal_secret: str | None = Field(
        default=None,
        validation_alias="N8N_INTERNAL_SECRET",
    )
    document_required_amount_threshold: float = Field(
        default=100.0,
        validation_alias="DOCUMENT_REQUIRED_AMOUNT_THRESHOLD",
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance de configuration mise en cache."""

    return Settings()
