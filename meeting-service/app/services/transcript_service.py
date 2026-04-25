"""Transkript-Verwaltung: Segmente speichern und Archiv abrufen."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Meeting, MeetingParticipant, TranscriptSegment


class TranscriptService:
    async def save_segment(
        self,
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
        participant_id: uuid.UUID,
        text: str,
        lang: str,
        translations: list[dict] | None = None,
        offset_ms: int = 0,
    ) -> TranscriptSegment:
        # Auto-increment sequence number
        max_seq = (
            await session.execute(
                select(func.coalesce(func.max(TranscriptSegment.sequence_num), 0)).where(
                    TranscriptSegment.meeting_id == meeting_id
                )
            )
        ).scalar_one()

        segment = TranscriptSegment(
            meeting_id=meeting_id,
            participant_id=participant_id,
            sequence_num=max_seq + 1,
            spoken_lang=lang,
            text=text,
            translations=translations,
            timestamp_offset_ms=offset_ms,
        )
        session.add(segment)
        await session.flush()
        return segment

    async def get_transcript(
        self, session: AsyncSession, *, meeting_id: uuid.UUID
    ) -> dict:
        meeting = (
            await session.execute(
                select(Meeting).where(Meeting.meeting_id == meeting_id)
            )
        ).scalar_one_or_none()

        if meeting is None:
            return {"meeting": None, "participants": [], "entries": []}

        participants = (
            await session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == meeting_id
                )
            )
        ).scalars().all()

        participant_map = {p.participant_id: p.display_name for p in participants}

        segments = (
            await session.execute(
                select(TranscriptSegment)
                .where(TranscriptSegment.meeting_id == meeting_id)
                .order_by(TranscriptSegment.sequence_num)
            )
        ).scalars().all()

        entries = []
        for seg in segments:
            # Convert offset_ms to MM:SS
            total_secs = seg.timestamp_offset_ms // 1000
            time_str = f"{total_secs // 60:02d}:{total_secs % 60:02d}"

            entries.append({
                "segment_id": seg.segment_id,
                "speaker": participant_map.get(seg.participant_id, "Unknown"),
                "time": time_str,
                "lang": seg.spoken_lang.upper(),
                "text": seg.text,
                "translations": seg.translations or [],
            })

        return {
            "meeting": meeting,
            "participants": participants,
            "entries": entries,
        }
