"""Magic-Link-Service: Anfordern und Verifizieren.

Sicherheitsprinzipien:
- User-Enumeration verhindert: ``request_link`` gibt keine Auskunft, ob die
  E-Mail existiert. Antwort ist immer gleich.
- Atomarer Token-Konsum via ``UPDATE ... RETURNING``.
- Token nur als SHA-256-Hash gespeichert.
- Rate-Limits pro E-Mail und pro IP, sowohl beim Anfordern als auch beim Verifizieren.
- Audit-Log mit AI-Act-konformer Kategorisierung.
"""
from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.audit import AuditAction, AuditEventCategory, write_audit
from app.core.config import Settings
from app.core.jwt import JWTIssuer
from app.core.logging import get_logger
from app.core.security import generate_token, hash_token
from app.db.models import (
    AIDisclosureAcknowledgment,
    MagicLinkToken,
    RefreshToken,
    Tenant,
    User,
)
from app.domain.errors import (
    MailerError,
    RateLimitExceeded,
    TokenExpiredOrUsed,
    TokenInvalid,
)
from app.mailer import Mailer
from app.services.rate_limiter import RateLimiter

log = get_logger(__name__)


@dataclass(frozen=True)
class RequestContext:
    ip_address: str | None
    user_agent: str | None


@dataclass(frozen=True)
class VerifyResult:
    user_id: uuid.UUID
    email: str
    ui_language: str
    role: str
    tenant_id: uuid.UUID | None
    tenant_risk_tier: str | None
    access_token: str
    refresh_token: str
    expires_in: int
    ai_disclosure_required: bool
    ai_disclosure_version: str | None


class MagicLinkService:
    def __init__(
        self,
        settings: Settings,
        mailer: Mailer,
        jwt_issuer: JWTIssuer,
        rate_limiter: RateLimiter,
    ) -> None:
        self._settings = settings
        self._mailer = mailer
        self._jwt = jwt_issuer
        self._rate_limiter = rate_limiter

    # -------------------------- request_link --------------------------------

    async def request_link(
        self,
        session: AsyncSession,
        *,
        email: str,
        ui_language: str,
        ctx: RequestContext,
    ) -> None:
        email = email.strip().lower()

        # 1. Rate-Limit: pro E-Mail und pro IP
        await self._enforce_request_rate_limits(email=email, ip=ctx.ip_address)

        # 2. User upserten — Magic Link erlaubt automatische Registrierung
        user = await self._upsert_user(session, email=email, ui_language=ui_language)

        # 3. Token erzeugen
        token_str = generate_token(byte_length=32)
        token_hash = hash_token(token_str)
        expires_at = datetime.now(tz=UTC) + timedelta(
            seconds=self._settings.magic_link_ttl_seconds
        )

        session.add(
            MagicLinkToken(
                token_hash=token_hash,
                email=email,
                user_id=user.user_id,
                purpose="login",
                ip_requested=ctx.ip_address,
                user_agent=ctx.user_agent,
                expires_at=expires_at,
            )
        )

        # 4. Audit-Eintrag (Kategorie: auth)
        tenant_risk_tier = await self._tenant_risk_tier(session, user.tenant_id)
        await write_audit(
            session,
            event_category=AuditEventCategory.AUTH,
            action=AuditAction.MAGIC_LINK_REQUESTED,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            tenant_risk_tier=tenant_risk_tier,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
        )

        await session.commit()

        # 5. Mail versenden — Fehler hier dürfen NICHT in die API-Antwort
        link = self._build_magic_url(token_str)
        try:
            await self._mailer.send_magic_link(
                to=email, ui_language=ui_language, link=link
            )
        except MailerError as exc:
            log.error("magic_link_mail_failed", email=email, error=str(exc))
            # Bewusst kein Re-Raise: Antwort an Client bleibt 202.

    async def _enforce_request_rate_limits(
        self, *, email: str, ip: str | None
    ) -> None:
        s = self._settings
        if not await self._rate_limiter.hit(
            f"magic:request:email:{email}",
            limit=s.magic_link_rate_per_email,
            window_seconds=s.magic_link_rate_window_seconds,
        ):
            raise RateLimitExceeded("Too many magic-link requests for this email.")
        if ip and not await self._rate_limiter.hit(
            f"magic:request:ip:{ip}",
            limit=s.magic_link_rate_per_ip,
            window_seconds=s.magic_link_rate_window_seconds,
        ):
            raise RateLimitExceeded("Too many magic-link requests from this IP.")

    async def _upsert_user(
        self, session: AsyncSession, *, email: str, ui_language: str
    ) -> User:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(email=email, ui_language=ui_language)
            session.add(user)
            await session.flush()
        return user

    async def _tenant_risk_tier(
        self, session: AsyncSession, tenant_id: uuid.UUID | None
    ) -> str | None:
        if tenant_id is None:
            return None
        result = await session.execute(
            select(Tenant.risk_tier).where(Tenant.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    def _build_magic_url(self, token: str) -> str:
        # Universal Link: öffnet die App, falls installiert; sonst Web-Fallback.
        return f"{self._settings.magic_link_base_url}/auth/magic?token={token}"

    # -------------------------- verify --------------------------------------

    async def verify(
        self,
        session: AsyncSession,
        *,
        token: str,
        ctx: RequestContext,
    ) -> VerifyResult:
        # 1. Format-Sanity (Brute-Force-Versuche frühzeitig abblocken)
        if not (40 <= len(token) <= 50):
            await self._record_failed_verify(session, ctx)
            raise TokenInvalid("Token format invalid.")

        # 2. Rate-Limit: fehlgeschlagene Verify-Versuche pro IP
        if ctx.ip_address and not await self._rate_limiter.hit(
            f"magic:verify:ip:{ctx.ip_address}",
            limit=self._settings.magic_link_verify_rate_per_ip,
            window_seconds=self._settings.magic_link_rate_window_seconds,
        ):
            raise RateLimitExceeded("Too many verify attempts from this IP.")

        # 3. Atomarer Konsum: SQL-UPDATE ... RETURNING
        token_hash_value = hash_token(token)
        consume_sql = text(
            """
            UPDATE magic_link_tokens
               SET used_at = now()
             WHERE token_hash = :h
               AND used_at IS NULL
               AND expires_at > now()
            RETURNING token_id, email, user_id, purpose, expires_at, used_at, created_at
            """
        )
        result = await session.execute(consume_sql, {"h": token_hash_value})
        row = result.first()
        if row is None:
            await self._record_failed_verify(session, ctx)
            await session.commit()
            raise TokenExpiredOrUsed("Token expired, used, or unknown.")

        user_id: uuid.UUID = row.user_id
        if user_id is None:
            await session.commit()
            raise TokenInvalid("Token has no associated user.")

        # 4. User laden
        user_result = await session.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalar_one()

        # E-Mail gilt nach erfolgreichem Magic-Link-Konsum als verifiziert.
        user.email_verified = True
        user.last_login_at = datetime.now(tz=UTC)

        # 5. JWTs ausstellen
        access_token = self._jwt.issue_access_token(
            user_id=user.user_id, email=user.email, ui_language=user.ui_language,
            role=user.role, tenant_id=user.tenant_id,
        )
        refresh_token, refresh_jti = self._jwt.issue_refresh_token(user.user_id)

        session.add(
            RefreshToken(
                token_jti_hash=hash_token(refresh_jti),
                user_id=user.user_id,
                expires_at=datetime.now(tz=UTC)
                + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
                user_agent=ctx.user_agent,
                ip_address=ctx.ip_address,
            )
        )

        # 6. AI-Disclosure-Status prüfen (Compliance-Hook)
        from app.compliance import CURRENT_DISCLOSURE_VERSION

        disclosure_ack = await session.execute(
            select(AIDisclosureAcknowledgment).where(
                AIDisclosureAcknowledgment.user_id == user.user_id,
                AIDisclosureAcknowledgment.disclosure_version
                == CURRENT_DISCLOSURE_VERSION,
            )
        )
        ai_disclosure_required = disclosure_ack.scalar_one_or_none() is None

        # 7. Audit-Eintrag
        tenant_risk_tier = await self._tenant_risk_tier(session, user.tenant_id)
        await write_audit(
            session,
            event_category=AuditEventCategory.AUTH,
            action=AuditAction.MAGIC_LINK_VERIFIED,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            tenant_risk_tier=tenant_risk_tier,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            extra_data={"ai_disclosure_required": ai_disclosure_required},
        )

        await session.commit()

        return VerifyResult(
            user_id=user.user_id,
            email=user.email,
            ui_language=user.ui_language,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_risk_tier=tenant_risk_tier,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._jwt.access_ttl_seconds,
            ai_disclosure_required=ai_disclosure_required,
            ai_disclosure_version=(
                CURRENT_DISCLOSURE_VERSION if ai_disclosure_required else None
            ),
        )

    async def _record_failed_verify(
        self, session: AsyncSession, ctx: RequestContext
    ) -> None:
        await write_audit(
            session,
            event_category=AuditEventCategory.AUTH,
            action=AuditAction.MAGIC_LINK_FAILED,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
        )

    async def acknowledge_disclosure(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        version: str,
        ctx: RequestContext,
        locale: str | None,
    ) -> None:
        # idempotent: Wenn bereits vorhanden, nichts tun
        existing = await session.execute(
            select(AIDisclosureAcknowledgment).where(
                AIDisclosureAcknowledgment.user_id == user_id,
                AIDisclosureAcknowledgment.disclosure_version == version,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return

        session.add(
            AIDisclosureAcknowledgment(
                user_id=user_id,
                disclosure_version=version,
                ip_address=ctx.ip_address,
                user_agent=ctx.user_agent,
                locale=locale,
            )
        )

        # Tenant-Risk-Tier für korrekte Retention-Klasse
        user = (
            await session.execute(select(User).where(User.user_id == user_id))
        ).scalar_one()
        tenant_risk_tier = await self._tenant_risk_tier(session, user.tenant_id)

        await write_audit(
            session,
            event_category=AuditEventCategory.COMPLIANCE,
            action=AuditAction.AI_DISCLOSURE_ACKNOWLEDGED,
            user_id=user_id,
            tenant_id=user.tenant_id,
            tenant_risk_tier=tenant_risk_tier,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            extra_data={"version": version, "locale": locale},
            # Compliance-Beleg dauerhaft aufbewahren
            retention_override="permanent",
        )

        await session.commit()

    # -------------------------- refresh -------------------------------------

    async def refresh(
        self,
        session: AsyncSession,
        *,
        refresh_token: str,
        ctx: RequestContext,
    ) -> tuple[str, str, int]:
        """Refresh-Token-Rotation: alten Token revozieren, neuen ausstellen."""
        from jose import JWTError

        try:
            claims = self._jwt.decode(refresh_token)
        except JWTError as exc:
            raise TokenInvalid(f"Refresh token invalid: {exc}") from exc

        if claims.get("typ") != "refresh":
            raise TokenInvalid("Wrong token type for refresh.")

        jti = claims.get("jti")
        sub = claims.get("sub")
        if not jti or not sub:
            raise TokenInvalid("Missing jti/sub in refresh token.")

        user_id = uuid.UUID(sub)
        jti_hash = hash_token(jti)

        # Atomar prüfen + revozieren in einer Transaktion
        existing = await session.execute(
            select(RefreshToken).where(RefreshToken.token_jti_hash == jti_hash)
        )
        row = existing.scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            raise TokenExpiredOrUsed("Refresh token unknown or already revoked.")
        if row.expires_at <= datetime.now(tz=UTC):
            raise TokenExpiredOrUsed("Refresh token expired.")

        # Alten Token revozieren
        row.revoked_at = datetime.now(tz=UTC)

        # Neue Tokens ausstellen
        user = (
            await session.execute(select(User).where(User.user_id == user_id))
        ).scalar_one()

        new_access = self._jwt.issue_access_token(
            user_id=user.user_id, email=user.email, ui_language=user.ui_language,
            role=user.role, tenant_id=user.tenant_id,
        )
        new_refresh, new_jti = self._jwt.issue_refresh_token(user.user_id)

        session.add(
            RefreshToken(
                token_jti_hash=hash_token(new_jti),
                user_id=user.user_id,
                expires_at=datetime.now(tz=UTC)
                + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
                user_agent=ctx.user_agent,
                ip_address=ctx.ip_address,
            )
        )

        tenant_risk_tier = await self._tenant_risk_tier(session, user.tenant_id)
        await write_audit(
            session,
            event_category=AuditEventCategory.AUTH,
            action=AuditAction.REFRESH,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            tenant_risk_tier=tenant_risk_tier,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
        )
        await session.commit()

        return new_access, new_refresh, self._jwt.access_ttl_seconds


def _b64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
