"""SQLAlchemy ORM-Modelle für den Meeting-Service."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── User Reference (owned by auth-service, read-only here) ───

class User(Base):
    """Minimale Referenz auf die users-Tabelle des Auth-Service."""
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)


# ── Meetings ──────────────────────────────────────────────────

class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('waiting','active','ended')",
            name="meeting_status_check",
        ),
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    target_langs: Mapped[list] = mapped_column(JSONB, nullable=False)
    join_code: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="waiting"
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    participants: Mapped[list[MeetingParticipant]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )


# ── Meeting Participants ──────────────────────────────────────

class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        CheckConstraint(
            "role IN ('host','participant')",
            name="participant_role_check",
        ),
    )

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="participant"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    meeting: Mapped[Meeting] = relationship(back_populates="participants")


# ── Transcript Segments ───────────────────────────────────────

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meeting_participants.participant_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)
    spoken_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    translations: Mapped[list | None] = mapped_column(JSONB)
    timestamp_offset_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    meeting: Mapped[Meeting] = relationship(back_populates="segments")


# ── Audit Log (shared table, read/write from meeting-service) ─

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    extra_data: Mapped[dict | None] = mapped_column(JSONB)
    retention_class: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="standard"
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
