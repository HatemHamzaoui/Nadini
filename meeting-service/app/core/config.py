"""Meeting-Service Konfiguration aus Umgebungsvariablen."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "nadini-meeting"
    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8002
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Datenbank (shared with auth-service)
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis (DB 1 to avoid collisions with auth-service on DB 0)
    redis_url: str = "redis://localhost:6379/1"

    # JWT Verification (via auth-service JWKS)
    jwks_url: str = "http://localhost:8001/.well-known/jwks.json"
    jwt_issuer: str = "http://localhost:8001"
    jwt_audience: str = "nadini"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Mailer
    mailer_driver: str = "console"  # "resend" or "console"
    resend_api_key: str = ""
    mail_from: str = "no-reply@nadini.ai"
    mail_from_name: str = "Nadini"
    frontend_base_url: str = "http://localhost:3000"

    # Rate Limiting
    meeting_create_rate_per_user: int = 10
    meeting_create_rate_window_seconds: int = 3600

    # WebSocket
    ws_ping_interval: int = 30
    ws_ping_timeout: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
