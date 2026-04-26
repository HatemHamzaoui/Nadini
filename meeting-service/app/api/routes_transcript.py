"""Transkript-Archiv Endpoint."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, get_session, get_transcript_service
from app.api.schemas import (
    MeetingOut,
    ParticipantOut,
    TranscriptArchiveResponse,
    TranscriptSegmentOut,
)
from app.services.transcript_service import TranscriptService

router = APIRouter(prefix="/meetings", tags=["transcripts"])


@router.get(
    "/{meeting_id}/transcript",
    response_model=TranscriptArchiveResponse,
    summary="Get full transcript archive for a meeting",
)
async def get_transcript(
    meeting_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[TranscriptService, Depends(get_transcript_service)],
) -> TranscriptArchiveResponse:
    result = await svc.get_transcript(session, meeting_id=meeting_id)

    if result["meeting"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    m = result["meeting"]
    duration = None
    if m.started_at and m.ended_at:
        duration = int((m.ended_at - m.started_at).total_seconds())

    return TranscriptArchiveResponse(
        meeting=MeetingOut(
            meeting_id=m.meeting_id,
            name=m.name,
            source_lang=m.source_lang,
            target_langs=m.target_langs,
            join_code=m.join_code,
            status=m.status,
            owner_id=m.owner_id,
            started_at=m.started_at,
            ended_at=m.ended_at,
            created_at=m.created_at,
            duration_seconds=duration,
        ),
        participants=[
            ParticipantOut(
                participant_id=p.participant_id,
                display_name=p.display_name,
                language=p.language,
                role=p.role,
                joined_at=p.joined_at,
                left_at=p.left_at,
            )
            for p in result["participants"]
        ],
        entries=[
            TranscriptSegmentOut(**e) for e in result["entries"]
        ],
    )


@router.get(
    "/{meeting_id}/summary",
    summary="Get AI-generated meeting summary",
)
async def get_summary(
    meeting_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[TranscriptService, Depends(get_transcript_service)],
    lang: str = "de",
) -> dict:
    from app.services.summarizer import format_summary_text, summarize_transcript
    from app.services.translation_service import translate_text

    result = await svc.get_transcript(session, meeting_id=meeting_id)
    if result["meeting"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    m = result["meeting"]
    duration = 0
    if m.started_at and m.ended_at:
        duration = int((m.ended_at - m.started_at).total_seconds())

    participants = [p.display_name for p in result["participants"]]
    languages = [m.source_lang] + (m.target_langs or [])

    summary = summarize_transcript(
        entries=result["entries"],
        meeting_name=m.name,
        duration_seconds=duration,
        participants=participants,
        languages=languages,
    )

    # Translate summary key points + action items to requested language
    translated_key_points = []
    for kp in summary.key_points:
        translated = translate_text(kp, m.source_lang, lang) if lang != m.source_lang else None
        translated_key_points.append({"original": kp, "translated": translated})

    formatted = format_summary_text(summary, lang=lang)

    return {
        "meeting_name": summary.title,
        "duration_minutes": summary.duration_minutes,
        "participant_count": summary.participant_count,
        "languages": summary.languages,
        "word_count": summary.word_count,
        "segment_count": summary.segment_count,
        "key_points": translated_key_points,
        "action_items": summary.action_items,
        "decisions": summary.decisions,
        "formatted_text": formatted,
    }
