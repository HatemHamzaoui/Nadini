"""WebSocket-Endpoint für Echtzeit-Transkript-Streaming."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_jwt_verifier, get_session, get_transcript_service, get_ws_manager
from app.core.jwt_verifier import JWTVerifier, JWTVerifyError
from app.core.logging import get_logger
from app.db.models import Meeting, MeetingParticipant
from app.services.transcript_service import TranscriptService
from app.services.ws_manager import WebSocketManager
from sqlalchemy import select

log = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/meetings/{meeting_id}/ws")
async def meeting_websocket(
    websocket: WebSocket,
    meeting_id: uuid.UUID,
    token: str = Query(...),
) -> None:
    # ── Auth ──
    jwt = get_jwt_verifier()
    try:
        claims = jwt.decode(token)
        user_id = uuid.UUID(claims["sub"])
    except (JWTVerifyError, KeyError, ValueError):
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # ── Get participant ──
    ws_mgr = get_ws_manager()

    # Get session manually (can't use Depends in WebSocket easily)
    from app.api.deps import state
    assert state.session_factory is not None
    async with state.session_factory() as session:
        participant = (
            await session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.left_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if participant is None:
            await websocket.close(code=4002, reason="Not a participant of this meeting")
            return

        meeting = (
            await session.execute(
                select(Meeting).where(Meeting.meeting_id == meeting_id)
            )
        ).scalar_one_or_none()

        if meeting is None or meeting.status == "ended":
            await websocket.close(code=4003, reason="Meeting not found or ended")
            return

    # ── Connect ──
    await ws_mgr.connect(meeting_id, participant.participant_id, websocket)

    # Broadcast join
    await ws_mgr.broadcast(
        meeting_id,
        {
            "type": "participant_joined",
            "participant_id": str(participant.participant_id),
            "name": participant.display_name,
            "language": participant.language,
        },
        exclude=participant.participant_id,
    )

    transcript_svc = TranscriptService()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "transcript_submit":
                text = msg.get("text", "").strip()
                lang = msg.get("lang", "").strip()
                if not text or not lang:
                    continue

                # Calculate offset
                offset_ms = 0
                if meeting.started_at:
                    offset_ms = int(
                        (datetime.now(timezone.utc) - meeting.started_at).total_seconds() * 1000
                    )

                # Translate to target languages
                translations = msg.get("translations", [])
                if not translations and meeting.target_langs:
                    try:
                        from app.services.translation_service import translate_to_targets
                        translations = translate_to_targets(text, lang, meeting.target_langs)
                    except Exception as exc:
                        log.warning("translation_error", error=str(exc))

                # Save segment
                async with state.session_factory() as session:
                    segment = await transcript_svc.save_segment(
                        session,
                        meeting_id=meeting_id,
                        participant_id=participant.participant_id,
                        text=text,
                        lang=lang,
                        translations=translations or None,
                        offset_ms=offset_ms,
                    )
                    await session.commit()

                    # Convert to time string
                    total_secs = offset_ms // 1000
                    time_str = f"{total_secs // 60:02d}:{total_secs % 60:02d}"

                    # Broadcast to all
                    await ws_mgr.broadcast(
                        meeting_id,
                        {
                            "type": "transcript",
                            "segment_id": str(segment.segment_id),
                            "speaker": participant.display_name,
                            "time": time_str,
                            "lang": lang.upper(),
                            "text": text,
                            "translations": translations,
                        },
                    )

            elif msg_type == "status_update":
                new_status = msg.get("status", "listening")
                await ws_mgr.broadcast(
                    meeting_id,
                    {
                        "type": "participant_status",
                        "participant_id": str(participant.participant_id),
                        "name": participant.display_name,
                        "status": new_status,
                    },
                    exclude=participant.participant_id,
                )

    except WebSocketDisconnect:
        pass
    finally:
        ws_mgr.disconnect(meeting_id, participant.participant_id)
        # Broadcast leave
        await ws_mgr.broadcast(
            meeting_id,
            {
                "type": "participant_left",
                "participant_id": str(participant.participant_id),
                "name": participant.display_name,
            },
        )
        log.info("ws_client_disconnected", meeting_id=str(meeting_id), user_id=str(user_id))
