"""SQLAlchemy Models — bilden das DB-Schema 1:1 ab.

Inkl. AI-Act-Compliance-Hooks (Hybrid-Pfad: Standard- und Hochrisiko-Tier).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Tenants — B2B-Mandanten mit Risk-Tier (AI-Act-Hybrid-Modell)
# ---------------------------------------------------------------------------


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('standard','high_risk_ready','high_risk_certified')",
            name="tenant_risk_tier_check",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_entity: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # AI-Act-Risk-Tier (Hybrid-Modell)
    risk_tier: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")

    # Frei deklarierter Use-Case beim Onboarding
    use_case_category: Mapped[str | None] = mapped_column(String(100))
    use_case_description: Mapped[str | None] = mapped_column(String(1000))

    # Vertrag und Acceptable Use Policy
    contract_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aup_version_accepted: Mapped[str | None] = mapped_column(String(20))

    # Hochrisiko-Bereitschaft (für späteres Tier-Upgrade)
    high_risk_assessment_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    fria_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Users — jetzt mit Tenant-Zuordnung
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ui_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="user")

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped[Tenant | None] = relationship()


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('login','register','email_change')",
            name="magic_link_purpose_check",
        ),
    )

    token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    token_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE")
    )
    purpose: Mapped[str] = mapped_column(String(20), default="login", nullable=False)
    ip_requested: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_jti_hash: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(INET)


class AIDisclosureAcknowledgment(Base):
    """Belegt, dass ein User über die KI-Natur informiert wurde
    und dies bestätigt hat (Art. 50(1) + (5) AI Act)."""

    __tablename__ = "ai_disclosure_acknowledgments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    disclosure_version: Mapped[str] = mapped_column(String(20), primary_key=True)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    locale: Mapped[str | None] = mapped_column(String(10))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "event_category IN ('auth','ai_interaction','compliance','admin','data_subject_request')",
            name="audit_event_category_check",
        ),
        CheckConstraint(
            "retention_class IN ('standard','extended_compliance','permanent')",
            name="audit_retention_class_check",
        ),
    )

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_category: Mapped[str] = mapped_column(String(30), nullable=False, default="auth")
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(1000))
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    extra_data: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    retention_class: Mapped[str] = mapped_column(
        String(30), nullable=False, default="standard"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
