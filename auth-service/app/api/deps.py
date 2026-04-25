"""FastAPI-Dependencies."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.jwt import JWTIssuer
from app.mailer import ConsoleMailer, Mailer, ResendMailer
from app.services.magic_link_service import MagicLinkService, RequestContext
from app.services.rate_limiter import RateLimiter


# Globale Singletons werden im Lifespan (main.py) gesetzt.
class AppState:
    session_factory: async_sessionmaker[AsyncSession] | None = None
    rate_limiter: RateLimiter | None = None
    jwt_issuer: JWTIssuer | None = None
    mailer: Mailer | None = None


state = AppState()


async def get_session() -> AsyncIterator[AsyncSession]:
    assert state.session_factory is not None, "Session factory not initialised."
    async with state.session_factory() as session:
        yield session


def get_settings_dep() -> Settings:
    return get_settings()


def get_jwt_issuer() -> JWTIssuer:
    assert state.jwt_issuer is not None
    return state.jwt_issuer


def get_rate_limiter() -> RateLimiter:
    assert state.rate_limiter is not None
    return state.rate_limiter


def get_mailer() -> Mailer:
    assert state.mailer is not None
    return state.mailer


def get_magic_link_service(
    settings: Annotated[Settings, Depends(get_settings_dep)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
    jwt: Annotated[JWTIssuer, Depends(get_jwt_issuer)],
    rate: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> MagicLinkService:
    return MagicLinkService(
        settings=settings, mailer=mailer, jwt_issuer=jwt, rate_limiter=rate
    )


def request_context(request: Request) -> RequestContext:
    """Extrahiert IP + UA aus dem Request für Audit-Zwecke."""
    ip = request.client.host if request.client else None
    # X-Forwarded-For nur, wenn Trusted-Proxy konfiguriert ist (Produktion).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        ip = fwd.split(",")[0].strip()
    return RequestContext(ip_address=ip, user_agent=request.headers.get("user-agent"))


def build_mailer(settings: Settings) -> Mailer:
    if settings.mailer_driver == "resend":
        return ResendMailer(
            api_key=settings.resend_api_key,
            from_email=settings.mail_from,
            from_name=settings.mail_from_name,
        )
    return ConsoleMailer(
        from_email=settings.mail_from, from_name=settings.mail_from_name
    )


# ---------------------------------------------------------------------------
# Auth-Dependency: extrahiert User aus Bearer-Token
# ---------------------------------------------------------------------------


async def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    jwt: Annotated[JWTIssuer, Depends(get_jwt_issuer)] = None,  # type: ignore[assignment]
) -> uuid.UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
    if claims.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type."
        )
    return uuid.UUID(claims["sub"])
