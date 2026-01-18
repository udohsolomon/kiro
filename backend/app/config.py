"""Application configuration using Pydantic settings."""

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
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
    secret_key: str = ""
    api_key_prefix: str = "kiro_"
    access_token_expire_minutes: int = 30

    # CORS - comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:5500"

    # Rate limiting
    rate_limit_requests: int = 100  # requests per minute for general endpoints
    rate_limit_submissions: int = 10  # submissions per minute

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

    # API URL (reachable from sandbox)
    api_url: str = "http://host.docker.internal:8000"

    # Google OAuth
    google_client_id: str = ""

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate and generate secret key if not provided."""
        if not v:
            # Generate a secure random key for development
            return secrets.token_hex(32)
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for security")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if self.debug:
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]





@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
