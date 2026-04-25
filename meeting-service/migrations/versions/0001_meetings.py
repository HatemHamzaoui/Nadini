"""Create meetings, meeting_participants, transcript_segments tables.

Revision ID: 0001
Create Date: 2026-04-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "m0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── meetings ──
    op.create_table(
        "meetings",
        sa.Column("meeting_id", UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_lang", sa.String(10), nullable=False),
        sa.Column("target_langs", JSONB, nullable=False),
        sa.Column("join_code", sa.String(12), nullable=False, unique=True, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("meeting_id"),
        sa.CheckConstraint("status IN ('waiting','active','ended')", name="meeting_status_check"),
    )

    # ── meeting_participants ──
    op.create_table(
        "meeting_participants",
        sa.Column("participant_id", UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("meeting_id", UUID(as_uuid=True), sa.ForeignKey("meetings.meeting_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="participant"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("participant_id"),
        sa.CheckConstraint("role IN ('host','participant')", name="participant_role_check"),
    )
    op.create_index("ix_participant_meeting_user", "meeting_participants", ["meeting_id", "user_id"])

    # ── transcript_segments ──
    op.create_table(
        "transcript_segments",
        sa.Column("segment_id", UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("meeting_id", UUID(as_uuid=True), sa.ForeignKey("meetings.meeting_id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_id", UUID(as_uuid=True), sa.ForeignKey("meeting_participants.participant_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_num", sa.Integer, nullable=False),
        sa.Column("spoken_lang", sa.String(10), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("translations", JSONB),
        sa.Column("timestamp_offset_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("segment_id"),
    )
    op.create_index("ix_segment_meeting_seq", "transcript_segments", ["meeting_id", "sequence_num"])


def downgrade() -> None:
    op.drop_table("transcript_segments")
    op.drop_table("meeting_participants")
    op.drop_table("meetings")
