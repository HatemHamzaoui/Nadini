"""Serious Incident Tracking (EU AI Act Art. 73).

Revision ID: m0008
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "m0008"
down_revision = "m0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "serious_incidents",
        sa.Column("incident_id", UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("reported_by", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),  # discrimination, functionality, privacy, safety
        sa.Column("severity", sa.String(20), nullable=False),  # critical, high, medium
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("affected_users_count", sa.Integer, nullable=True),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("remediation_steps", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),  # open, investigating, resolved
        sa.Column("authority_notified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("authority_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authority_reference", sa.String(100), nullable=True),
        sa.Column("extra_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("incident_id"),
        sa.CheckConstraint("category IN ('discrimination','functionality','privacy','safety','quality')", name="incident_category_check"),
        sa.CheckConstraint("severity IN ('critical','high','medium')", name="incident_severity_check"),
        sa.CheckConstraint("status IN ('open','investigating','resolved','closed')", name="incident_status_check"),
    )


def downgrade() -> None:
    op.drop_table("serious_incidents")
