"""Konfiguration aus Umgebungsvariablen."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "nadini-auth"
    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Datenbank
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_private_key_path: Path
    jwt_public_key_path: Path
    jwt_issuer: str
    jwt_audience: str = "nadini"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000

    # Magic Link
    magic_link_base_url: str
    magic_link_ttl_seconds: int = 300
    magic_link_rate_per_email: int = 3
    magic_link_rate_per_ip: int = 10
    magic_link_rate_window_seconds: int = 900
    magic_link_verify_rate_per_ip: int = 10

    # Mailer
    mailer_driver: Literal["resend", "console"] = "resend"
    resend_api_key: str = ""
    mail_from: str = "no-reply@nadini.ai"
    mail_from_name: str = "Nadini"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @field_validator("cors_origins")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
