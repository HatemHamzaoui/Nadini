"""Meeting CRUD + Join/End Endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    current_user_id,
    get_meeting_service,
    get_session,
    request_context,
)
from app.api.schemas import (
    CreateMeetingRequest,
    JoinMeetingRequest,
    JoinMeetingResponse,
    MeetingCreatedResponse,
    MeetingOut,
)
from app.domain.errors import (
    MeetingEnded,
    MeetingNotFound,
    NotAuthorized,
    RateLimitExceeded,
)
from app.services.meeting_service import MeetingService, RequestContext

router = APIRouter(prefix="/meetings", tags=["meetings"], redirect_slashes=False)


@router.post(
    "",
    response_model=MeetingCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new meeting",
)
async def create_meeting(
    payload: CreateMeetingRequest,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MeetingService, Depends(get_meeting_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> MeetingCreatedResponse:
    try:
        meeting = await svc.create_meeting(
            session,
            owner_id=user_id,
            name=payload.name,
            source_lang=payload.source_lang,
            target_langs=payload.target_langs,
            ctx=ctx,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many meetings created. Please try again later.",
        )
    return MeetingCreatedResponse(
        meeting_id=meeting.meeting_id,
        join_code=meeting.join_code,
        name=meeting.name,
        status=meeting.status,
    )


@router.get(
    "",
    response_model=list[MeetingOut],
    summary="List meetings for the current user",
)
async def list_meetings(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MeetingService, Depends(get_meeting_service)],
) -> list[MeetingOut]:
    rows = await svc.list_meetings(session, user_id=user_id)
    return [
        MeetingOut(
            meeting_id=r["meeting"].meeting_id,
            name=r["meeting"].name,
            source_lang=r["meeting"].source_lang,
            target_langs=r["meeting"].target_langs,
            join_code=r["meeting"].join_code,
            status=r["meeting"].status,
            owner_id=r["meeting"].owner_id,
            participant_count=r["participant_count"],
            started_at=r["meeting"].started_at,
            ended_at=r["meeting"].ended_at,
            created_at=r["meeting"].created_at,
            duration_seconds=r["duration_seconds"],
        )
        for r in rows
    ]


@router.get(
    "/{meeting_id}",
    response_model=MeetingOut,
    summary="Get meeting details",
)
async def get_meeting(
    meeting_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MeetingService, Depends(get_meeting_service)],
) -> MeetingOut:
    try:
        meeting = await svc.get_meeting(session, meeting_id=meeting_id, user_id=user_id)
    except MeetingNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    duration = None
    if meeting.started_at and meeting.ended_at:
        duration = int((meeting.ended_at - meeting.started_at).total_seconds())

    return MeetingOut(
        meeting_id=meeting.meeting_id,
        name=meeting.name,
        source_lang=meeting.source_lang,
        target_langs=meeting.target_langs,
        join_code=meeting.join_code,
        status=meeting.status,
        owner_id=meeting.owner_id,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        created_at=meeting.created_at,
        duration_seconds=duration,
    )


@router.post(
    "/{meeting_id}/join",
    response_model=JoinMeetingResponse,
    summary="Join a meeting",
)
async def join_meeting(
    meeting_id: uuid.UUID,
    payload: JoinMeetingRequest,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MeetingService, Depends(get_meeting_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> JoinMeetingResponse:
    try:
        participant = await svc.join_meeting(
            session,
            meeting_id=meeting_id,
            user_id=user_id,
            display_name=payload.display_name,
            language=payload.language,
            ctx=ctx,
        )
    except MeetingNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    except MeetingEnded:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Meeting has ended")

    return JoinMeetingResponse(
        participant_id=participant.participant_id,
        meeting_id=meeting_id,
        display_name=participant.display_name,
        language=participant.language,
        role=participant.role,
        ws_url=f"/meetings/{meeting_id}/ws",
    )


@router.post(
    "/{meeting_id}/end",
    status_code=status.HTTP_200_OK,
    summary="End a meeting (host only)",
)
async def end_meeting(
    meeting_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MeetingService, Depends(get_meeting_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> dict:
    try:
        meeting = await svc.end_meeting(session, meeting_id=meeting_id, user_id=user_id, ctx=ctx)
    except MeetingNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    except NotAuthorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can end the meeting")

    duration = None
    if meeting.started_at and meeting.ended_at:
        duration = int((meeting.ended_at - meeting.started_at).total_seconds())

    return {"status": "ended", "duration_seconds": duration}
