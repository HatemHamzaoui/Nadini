"""FastAPI-App: Initialisierung, Lifespan, Middleware, Router-Registrierung."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api import deps
from app.api.routes_auth import router as auth_router
from app.api.routes_admin import router as admin_router
from app.api.routes_compliance import router as compliance_router
from app.api.routes_misc import router as misc_router
from app.core.config import get_settings
from app.core.jwt import JWTIssuer
from app.core.logging import configure_logging, get_logger
from app.db.session import create_engine, create_session_factory
from app.services.rate_limiter import RedisRateLimiter

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)

    log.info("auth_service_starting", env=settings.app_env)

    # Engine + Session Factory
    engine = create_engine(settings)
    deps.state.session_factory = create_session_factory(engine)

    # Redis + Rate-Limiter
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    deps.state.rate_limiter = RedisRateLimiter(redis)

    # JWT-Issuer (lädt RS256-Schlüssel)
    deps.state.jwt_issuer = JWTIssuer(settings)

    # Mailer
    deps.state.mailer = deps.build_mailer(settings)

    log.info("auth_service_ready")

    try:
        yield
    finally:
        log.info("auth_service_shutting_down")
        await redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Nadini Auth Service",
        version="0.1.0",
        description=(
            "Magic-Link-Login mit AI-Act-Compliance-Hooks (Art. 50 AI Act). "
            "Hybrid-Risk-Tier-Modell für B2B-Tenants."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", error=str(exc), error_type=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error"},
        )

    app.include_router(misc_router)
    app.include_router(auth_router)
    app.include_router(compliance_router)
    app.include_router(admin_router)

    return app


app = create_app()
