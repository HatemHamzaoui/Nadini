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
