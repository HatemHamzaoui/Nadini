"""Meeting-Service: FastAPI-App mit WebSocket-Support."""
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
from app.api.routes_meetings import router as meetings_router
from app.api.routes_misc import router as misc_router
from app.api.routes_providers import router as providers_router
from app.api.routes_transcript import router as transcript_router
from app.api.routes_ws import router as ws_router
from app.core.config import get_settings
from app.core.jwt_verifier import JWTVerifier
from app.core.logging import configure_logging, get_logger
from app.db.session import create_engine, create_session_factory
from app.services.rate_limiter import RedisRateLimiter
from app.services.ws_manager import WebSocketManager

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)

    log.info("meeting_service_starting", env=settings.app_env)

    # DB
    engine = create_engine(settings)
    deps.state.session_factory = create_session_factory(engine)

    # Redis
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    deps.state.rate_limiter = RedisRateLimiter(redis)

    # JWT Verifier (fetch JWKS from auth-service)
    jwt_verifier = JWTVerifier(
        jwks_url=settings.jwks_url,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    try:
        await jwt_verifier.refresh_keys()
    except Exception as exc:
        log.warning("jwks_fetch_failed_at_startup", error=str(exc))
    deps.state.jwt_verifier = jwt_verifier

    # WebSocket Manager
    deps.state.ws_manager = WebSocketManager()

    # Translation Routing Engine
    try:
        from app.translation.health_monitor import HealthMonitor
        from app.translation.registry import ProviderRegistry
        from app.translation.router import TranslationRouter

        registry = ProviderRegistry()
        async with deps.state.session_factory() as session:
            await registry.load_from_db(session)
        registry.init_argos()  # Download argos packages if needed

        health_monitor = HealthMonitor(registry, redis, interval=settings.health_check_interval_seconds)
        translation_router = TranslationRouter(registry, health_monitor)
        async with deps.state.session_factory() as session:
            await translation_router.load_routes(session)

        deps.state.provider_registry = registry
        deps.state.health_monitor = health_monitor
        deps.state.translation_router = translation_router

        await health_monitor.start()

        # Quality Monitor
        from app.translation.quality import QualityMonitor
        deps.state.quality_monitor = QualityMonitor(redis)
    except Exception as exc:
        log.warning("translation_engine_init_failed", error=str(exc))

    log.info("meeting_service_ready")

    try:
        yield
    finally:
        log.info("meeting_service_shutting_down")
        if deps.state.health_monitor:
            await deps.state.health_monitor.stop()
        await redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Nadini Meeting Service",
        version="0.1.0",
        description="Meeting-CRUD, Teilnehmer-Management und WebSocket-Transkript-Streaming.",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
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
    app.include_router(meetings_router)
    app.include_router(transcript_router)
    app.include_router(providers_router)
    app.include_router(ws_router)

    return app


app = create_app()
