"""Tenant onboarding: logo, defaults, glossary.

Revision ID: 0003
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("logo_url", sa.String(500), nullable=True))
    op.add_column("tenants", sa.Column("default_source_lang", sa.String(10), nullable=True, server_default="de"))
    op.add_column("tenants", sa.Column("default_target_langs", JSONB, nullable=True))
    op.add_column("tenants", sa.Column("custom_glossary", JSONB, nullable=True))
    op.add_column("tenants", sa.Column("max_users", sa.Integer, nullable=True))
    op.add_column("tenants", sa.Column("plan", sa.String(20), nullable=False, server_default="starter"))


def downgrade() -> None:
    op.drop_column("tenants", "plan")
    op.drop_column("tenants", "max_users")
    op.drop_column("tenants", "custom_glossary")
    op.drop_column("tenants", "default_target_langs")
    op.drop_column("tenants", "default_source_lang")
    op.drop_column("tenants", "logo_url")
