"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Kiro Labyrinth"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kiro_labyrinth"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    api_key_prefix: str = "kiro_"
    access_token_expire_minutes: int = 30

    # Sandbox
    sandbox_timeout_seconds: int = 300
    sandbox_memory_limit_mb: int = 256
    max_concurrent_sandboxes: int = 50

    # Email (mock in development)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = "noreply@kiro-labyrinth.dev"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
