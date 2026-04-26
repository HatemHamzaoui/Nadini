"""Dependency Injection für den Meeting-Service."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.jwt_verifier import JWTVerifier, JWTVerifyError
from app.services.meeting_service import MeetingService, RequestContext
from app.services.rate_limiter import RateLimiter
from app.services.transcript_service import TranscriptService
from app.services.ws_manager import WebSocketManager
from fastapi import Request


class AppState:
    session_factory: async_sessionmaker[AsyncSession] | None = None
    rate_limiter: RateLimiter | None = None
    jwt_verifier: JWTVerifier | None = None
    ws_manager: WebSocketManager | None = None
    translation_router: object | None = None  # TranslationRouter
    health_monitor: object | None = None  # HealthMonitor
    provider_registry: object | None = None  # ProviderRegistry
    quality_monitor: object | None = None  # QualityMonitor


state = AppState()


# ── Session ──

async def get_session() -> AsyncIterator[AsyncSession]:
    assert state.session_factory is not None
    async with state.session_factory() as session:
        yield session


# ── Settings ──

def get_settings_dep() -> Settings:
    return get_settings()


# ── JWT (HTTP) ──

def get_jwt_verifier() -> JWTVerifier:
    assert state.jwt_verifier is not None
    return state.jwt_verifier


async def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    jwt: Annotated[JWTVerifier, Depends(get_jwt_verifier)] = None,
) -> uuid.UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(token)
    except JWTVerifyError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )
    return uuid.UUID(claims["sub"])


# ── JWT with Role ──

async def current_user_with_role(
    authorization: Annotated[str | None, Header()] = None,
    jwt: Annotated[JWTVerifier, Depends(get_jwt_verifier)] = None,
) -> tuple[uuid.UUID, str]:
    """Returns (user_id, role)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(token)
    except JWTVerifyError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")
    return uuid.UUID(claims["sub"]), claims.get("role", "user")


async def require_admin(
    user_and_role: Annotated[tuple[uuid.UUID, str], Depends(current_user_with_role)],
) -> uuid.UUID:
    """403 if not admin."""
    user_id, role = user_and_role
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user_id


async def require_moderator_or_above(
    user_and_role: Annotated[tuple[uuid.UUID, str], Depends(current_user_with_role)],
) -> uuid.UUID:
    """403 if not moderator, tenant_admin, or admin."""
    user_id, role = user_and_role
    if role not in ("moderator", "tenant_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator or higher role required.")
    return user_id


async def require_interpreter_or_admin(
    user_and_role: Annotated[tuple[uuid.UUID, str], Depends(current_user_with_role)],
) -> uuid.UUID:
    """403 if not interpreter or admin."""
    user_id, role = user_and_role
    if role not in ("interpreter", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Interpreter or admin role required.")
    return user_id


async def require_not_guest(
    user_and_role: Annotated[tuple[uuid.UUID, str], Depends(current_user_with_role)],
) -> uuid.UUID:
    """403 if guest."""
    user_id, role = user_and_role
    if role == "guest":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guests cannot perform this action.")
    return user_id


# ── JWT (WebSocket) ──

async def ws_user_id(
    token: Annotated[str, Query()],
    jwt: Annotated[JWTVerifier, Depends(get_jwt_verifier)] = None,
) -> uuid.UUID:
    try:
        claims = jwt.decode(token)
    except JWTVerifyError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return uuid.UUID(claims["sub"])


# ── Request Context ──

def request_context(request: Request) -> RequestContext:
    ip = request.client.host if request.client else None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        ip = fwd.split(",")[0].strip()
    return RequestContext(ip_address=ip, user_agent=request.headers.get("user-agent"))


# ── Services ──

def get_meeting_service(
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> MeetingService:
    assert state.rate_limiter is not None
    return MeetingService(settings=settings, rate_limiter=state.rate_limiter)


def get_transcript_service() -> TranscriptService:
    return TranscriptService()


def get_ws_manager() -> WebSocketManager:
    assert state.ws_manager is not None
    return state.ws_manager
