"""Add scheduling fields to meetings table.

Revision ID: m0002
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "m0002"
down_revision = "m0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("meetings", sa.Column("description", sa.Text, nullable=True))
    op.add_column("meetings", sa.Column("invited_emails", JSONB, nullable=True))
    # Update status check to include 'scheduled'
    op.drop_constraint("meeting_status_check", "meetings", type_="check")
    op.create_check_constraint(
        "meeting_status_check", "meetings",
        "status IN ('scheduled','waiting','active','ended')"
    )


def downgrade() -> None:
    op.drop_constraint("meeting_status_check", "meetings", type_="check")
    op.create_check_constraint(
        "meeting_status_check", "meetings",
        "status IN ('waiting','active','ended')"
    )
    op.drop_column("meetings", "invited_emails")
    op.drop_column("meetings", "description")
    op.drop_column("meetings", "scheduled_at")
