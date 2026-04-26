"""Pydantic v2 Request/Response-Modelle für den Meeting-Service."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Requests ──

class CreateMeetingRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(..., min_length=1, max_length=200)
    source_lang: str = Field(..., min_length=2, max_length=10)
    target_langs: list[str] = Field(..., min_length=1, max_length=20)
    scheduled_at: datetime | None = None
    description: str | None = Field(default=None, max_length=1000)
    invited_emails: list[str] | None = None


class JoinMeetingRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    display_name: str = Field(..., min_length=1, max_length=100)
    language: str = Field(..., min_length=2, max_length=10)


# ── Responses ──

class MeetingOut(BaseModel):
    meeting_id: uuid.UUID
    name: str
    source_lang: str
    target_langs: list[str]
    join_code: str
    status: str
    owner_id: uuid.UUID
    participant_count: int = 0
    scheduled_at: datetime | None = None
    description: str | None = None
    invited_emails: list[str] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    duration_seconds: int | None = None


class MeetingCreatedResponse(BaseModel):
    meeting_id: uuid.UUID
    join_code: str
    name: str
    status: str


class JoinMeetingResponse(BaseModel):
    participant_id: uuid.UUID
    meeting_id: uuid.UUID
    display_name: str
    language: str
    role: str
    ws_url: str


class ParticipantOut(BaseModel):
    participant_id: uuid.UUID
    display_name: str
    language: str
    role: str
    joined_at: datetime
    left_at: datetime | None = None


class TranscriptSegmentOut(BaseModel):
    segment_id: uuid.UUID
    speaker: str
    time: str
    lang: str
    text: str
    translations: list[dict] | None = None


class TranscriptArchiveResponse(BaseModel):
    meeting: MeetingOut
    participants: list[ParticipantOut]
    entries: list[TranscriptSegmentOut]
