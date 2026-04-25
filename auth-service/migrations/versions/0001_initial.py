"""initial schema mit AI-Act-Compliance-Hooks

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25 12:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ---- tenants ----
    op.create_table(
        "tenants",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("legal_entity", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column(
            "risk_tier",
            sa.String(30),
            nullable=False,
            server_default="standard",
        ),
        sa.Column("use_case_category", sa.String(100), nullable=True),
        sa.Column("use_case_description", sa.String(1000), nullable=True),
        sa.Column("contract_signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aup_version_accepted", sa.String(20), nullable=True),
        sa.Column(
            "high_risk_assessment_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("fria_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "risk_tier IN ('standard','high_risk_ready','high_risk_certified')",
            name="tenant_risk_tier_check",
        ),
    )
    op.create_index("ix_tenants_risk_tier", "tenants", ["risk_tier"])

    # ---- users ----
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("ui_language", sa.String(10), nullable=False, server_default="en"),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ---- magic_link_tokens ----
    op.create_table(
        "magic_link_tokens",
        sa.Column(
            "token_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="login"),
        sa.Column("ip_requested", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "purpose IN ('login','register','email_change')",
            name="magic_link_purpose_check",
        ),
    )
    op.create_index(
        "ix_magic_link_tokens_token_hash",
        "magic_link_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index("ix_magic_link_tokens_email", "magic_link_tokens", ["email"])
    op.create_index(
        "ix_magic_link_tokens_active_expires",
        "magic_link_tokens",
        ["expires_at"],
        postgresql_where=sa.text("used_at IS NULL"),
    )

    # ---- refresh_tokens ----
    op.create_table(
        "refresh_tokens",
        sa.Column("token_jti_hash", sa.LargeBinary(32), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ---- ai_disclosure_acknowledgments (Art. 50(1)+(5) AI Act) ----
    op.create_table(
        "ai_disclosure_acknowledgments",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("disclosure_version", sa.String(20), primary_key=True),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("locale", sa.String(10), nullable=True),
    )

    # ---- audit_logs (erweitert um AI-Act-Felder) ----
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "event_category",
            sa.String(30),
            nullable=False,
            server_default="auth",
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("detail", sa.String(1000), nullable=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "retention_class",
            sa.String(30),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "event_category IN ('auth','ai_interaction','compliance','admin','data_subject_request')",
            name="audit_event_category_check",
        ),
        sa.CheckConstraint(
            "retention_class IN ('standard','extended_compliance','permanent')",
            name="audit_retention_class_check",
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_event_category", "audit_logs", ["event_category"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ai_disclosure_acknowledgments")
    op.drop_table("refresh_tokens")
    op.drop_table("magic_link_tokens")
    op.drop_table("users")
    op.drop_table("tenants")
