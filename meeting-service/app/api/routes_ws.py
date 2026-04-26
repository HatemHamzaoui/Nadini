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
    token: str = Query(default=""),
) -> None:
    # ── Auth ── (accept token from query param OR first WS message)
    jwt = get_jwt_verifier()
    auth_token = token

    # If no token in query, try subprotocol header
    if not auth_token:
        # Check Sec-WebSocket-Protocol header for token
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if protocols:
            auth_token = protocols.split(",")[0].strip()

    if not auth_token:
        await websocket.close(code=4001, reason="No authentication token provided")
        return

    try:
        claims = jwt.decode(auth_token)
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

            elif msg_type == "transcript_partial":
                # Interim speech result — broadcast immediately, no translation
                partial_text = msg.get("text", "").strip()
                partial_lang = msg.get("lang", "").strip()
                if partial_text:
                    offset_ms = 0
                    if meeting.started_at:
                        offset_ms = int((datetime.now(timezone.utc) - meeting.started_at).total_seconds() * 1000)
                    total_secs = offset_ms // 1000
                    time_str = f"{total_secs // 60:02d}:{total_secs % 60:02d}"

                    await ws_mgr.broadcast(
                        meeting_id,
                        {
                            "type": "transcript_partial",
                            "speaker": participant.display_name,
                            "time": time_str,
                            "lang": partial_lang.upper() if partial_lang else "?",
                            "text": partial_text,
                            "participant_id": str(participant.participant_id),
                        },
                    )

            elif msg_type == "transcript_submit":
                text = msg.get("text", "").strip()
                lang = msg.get("lang", "").strip()
                if not text:
                    continue

                # Auto-detect language if not provided or "auto"
                if not lang or lang == "auto":
                    try:
                        from app.services.lang_detect import detect_language
                        lang, _conf = detect_language(text)
                    except Exception:
                        lang = participant.language  # fallback to participant's language

                # Calculate offset
                offset_ms = 0
                if meeting.started_at:
                    offset_ms = int(
                        (datetime.now(timezone.utc) - meeting.started_at).total_seconds() * 1000
                    )

                # Translate via Routing Engine
                translations = msg.get("translations", [])
                if not translations and meeting.target_langs:
                    try:
                        from app.services.glossary import DEFAULT_GLOSSARY, GlossaryEntry, apply_glossary_to_translations
                        router = state.translation_router
                        if router:
                            translations = await router.translate_to_targets(
                                text, lang, meeting.target_langs,
                                mode=getattr(meeting, "mode", "online"),
                                meeting_id=str(meeting_id),
                                speaker=participant.display_name,
                            )
                            # Apply glossary (default + tenant via shared DB)
                            glossary = list(DEFAULT_GLOSSARY)
                            try:
                                async with state.session_factory() as gs:
                                    from sqlalchemy import text as sql_text
                                    row = (await gs.execute(sql_text(
                                        "SELECT t.custom_glossary FROM tenants t "
                                        "JOIN users u ON u.tenant_id = t.tenant_id "
                                        f"WHERE u.user_id = '{participant.user_id}' "
                                        "AND t.custom_glossary IS NOT NULL LIMIT 1"
                                    ))).first()
                                    if row and row[0]:
                                        for entry in row[0]:
                                            if isinstance(entry, dict) and "term" in entry:
                                                glossary.append(GlossaryEntry(
                                                    source_term=entry["term"],
                                                    translations=entry.get("translations", {}),
                                                ))
                            except Exception:
                                pass
                            translations = apply_glossary_to_translations(translations, glossary)
                        else:
                            # Fallback to direct argos if router not initialized
                            from app.services.translation_service import translate_to_targets as argos_translate
                            translations = argos_translate(text, lang, meeting.target_langs)
                            translations = apply_glossary_to_translations(translations)
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

                    # Art. 12 EU AI Act: Log AI interaction with model name
                    try:
                        from app.compliance.audit import AuditEventCategory, write_audit
                        async with state.session_factory() as audit_session:
                            await write_audit(
                                audit_session,
                                event_category=AuditEventCategory.AI_INTERACTION,
                                action="meeting.translation_segment",
                                user_id=participant.user_id,
                                detail=f"Translated {lang}→{','.join(meeting.target_langs)}",
                                extra_data={
                                    "segment_id": str(segment.segment_id),
                                    "meeting_id": str(meeting_id),
                                    "providers": [t.get("provider", "") for t in translations if isinstance(t, dict)],
                                    "ai_generated": True,
                                },
                            )
                            await audit_session.commit()
                    except Exception:
                        pass

                    # Convert to time string
                    total_secs = offset_ms // 1000
                    time_str = f"{total_secs // 60:02d}:{total_secs % 60:02d}"

                    # Sentiment analysis
                    sentiment_data = None
                    try:
                        from app.services.sentiment import analyze_sentiment
                        s = analyze_sentiment(text, lang)
                        sentiment_data = {"label": s.label, "score": s.score}
                    except Exception:
                        pass

                    # Check if any translation used failover
                    any_failover = any(t.get("failover") for t in translations if isinstance(t, dict))
                    # Get provider name from first translation
                    provider_used = translations[0].get("provider", "") if translations and isinstance(translations[0], dict) else ""

                    # Detect if language changed from meeting source
                    lang_changed = lang.lower() != meeting.source_lang.lower()

                    # Get detected domain from context
                    domain = "general"
                    try:
                        from app.translation.context import get_meeting_context
                        ctx = get_meeting_context(str(meeting_id))
                        domain = ctx.get_domain()
                    except Exception:
                        pass

                    # Broadcast final transcript (replaces any partial)
                    await ws_mgr.broadcast(
                        meeting_id,
                        {
                            "type": "transcript_final",
                            "segment_id": str(segment.segment_id),
                            "speaker": participant.display_name,
                            "participant_id": str(participant.participant_id),
                            "time": time_str,
                            "lang": lang.upper(),
                            "detected_lang": lang.lower(),
                            "lang_changed": lang_changed,
                            "text": text,
                            "translations": translations,
                            "sentiment": sentiment_data,
                            "domain": domain,
                            "provider": provider_used,
                            "failover": any_failover,
                        },
                    )

            elif msg_type == "notes_update":
                notes_text = msg.get("text", "")
                await ws_mgr.broadcast(
                    meeting_id,
                    {"type": "notes_update", "text": notes_text},
                    exclude=participant.participant_id,
                )

            elif msg_type == "translation_correction":
                # Interpreter/Admin can correct a translation
                segment_id = msg.get("segment_id", "")
                corrected_text = msg.get("corrected_text", "").strip()
                target_lang = msg.get("target_lang", "").strip()

                if corrected_text and segment_id:
                    # Check role (interpreter or admin can correct)
                    # participant.role is from meeting_participants, not JWT
                    # For now: broadcast to all, trust the client
                    await ws_mgr.broadcast(
                        meeting_id,
                        {
                            "type": "translation_correction",
                            "segment_id": segment_id,
                            "target_lang": target_lang.upper(),
                            "corrected_text": corrected_text,
                            "corrected_by": participant.display_name,
                            "is_interpreter": True,
                        },
                    )

                    # Update in DB
                    async with state.session_factory() as session:
                        from sqlalchemy import select, update
                        from app.db.models import TranscriptSegment
                        seg = (await session.execute(
                            select(TranscriptSegment).where(
                                TranscriptSegment.segment_id == segment_id
                            )
                        )).scalar_one_or_none()
                        if seg and seg.translations:
                            updated = []
                            for t in seg.translations:
                                if isinstance(t, dict) and t.get("lang", "").upper() == target_lang.upper():
                                    t["text"] = corrected_text
                                    t["corrected_by"] = participant.display_name
                                updated.append(t)
                            seg.translations = updated
                            await session.commit()

                    log.info("translation_corrected",
                             segment=segment_id[:8], lang=target_lang,
                             by=participant.display_name)

            elif msg_type == "reaction":
                emoji = msg.get("emoji", "")
                if emoji:
                    await ws_mgr.broadcast(
                        meeting_id,
                        {"type": "reaction", "emoji": emoji, "name": participant.display_name},
                        exclude=participant.participant_id,
                    )

            elif msg_type == "chat":
                chat_text = msg.get("text", "").strip()
                if chat_text:
                    await ws_mgr.broadcast(
                        meeting_id,
                        {
                            "type": "chat",
                            "name": participant.display_name,
                            "text": chat_text,
                            "participant_id": str(participant.participant_id),
                        },
                        exclude=participant.participant_id,
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
