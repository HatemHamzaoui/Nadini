"""Meeting-Service Business Logic."""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.audit import AuditAction, AuditEventCategory, write_audit
from app.core.config import Settings
from app.core.logging import get_logger
from app.db.models import Meeting, MeetingParticipant, User

log = get_logger(__name__)
from app.domain.errors import MeetingEnded, MeetingNotFound, NotAuthorized, RateLimitExceeded
from app.services.rate_limiter import RateLimiter


@dataclass(frozen=True)
class RequestContext:
    ip_address: str | None = None
    user_agent: str | None = None


class MeetingService:
    def __init__(self, settings: Settings, rate_limiter: RateLimiter) -> None:
        self._settings = settings
        self._rate_limiter = rate_limiter

    def _generate_join_code(self) -> str:
        return secrets.token_urlsafe(6)[:8]

    async def create_meeting(
        self,
        session: AsyncSession,
        *,
        owner_id: uuid.UUID,
        name: str,
        source_lang: str,
        target_langs: list[str],
        ctx: RequestContext,
        scheduled_at: datetime | None = None,
        description: str | None = None,
        invited_emails: list[str] | None = None,
    ) -> Meeting:
        # Rate limit
        if not await self._rate_limiter.hit(
            f"meeting:create:{owner_id}",
            limit=self._settings.meeting_create_rate_per_user,
            window_seconds=self._settings.meeting_create_rate_window_seconds,
        ):
            raise RateLimitExceeded("Too many meetings created")

        # Generate unique join code (retry on collision)
        for _ in range(5):
            join_code = self._generate_join_code()
            existing = await session.execute(
                select(Meeting.meeting_id).where(Meeting.join_code == join_code)
            )
            if existing.scalar_one_or_none() is None:
                break
        else:
            join_code = secrets.token_urlsafe(8)[:12]

        is_scheduled = scheduled_at is not None
        meeting = Meeting(
            owner_id=owner_id,
            name=name,
            source_lang=source_lang,
            target_langs=target_langs,
            join_code=join_code,
            status="scheduled" if is_scheduled else "active",
            scheduled_at=scheduled_at,
            description=description,
            invited_emails=invited_emails,
            started_at=None if is_scheduled else datetime.now(timezone.utc),
        )
        session.add(meeting)
        await session.flush()

        await write_audit(
            session,
            event_category=AuditEventCategory.AI_INTERACTION,
            action=AuditAction.MEETING_CREATED,
            user_id=owner_id,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            detail=f"Meeting '{name}' created",
            extra_data={"meeting_id": str(meeting.meeting_id), "join_code": join_code},
        )
        await session.commit()

        # Send invitation emails (fire-and-forget, don't block meeting creation)
        if invited_emails:
            try:
                from app.services.mailer import send_meeting_invites
                join_url = f"{self._settings.frontend_base_url}/app/join.html?m={meeting.meeting_id}"
                # Get owner email for host_name
                owner = (await session.execute(
                    select(User).where(User.user_id == owner_id)
                )).scalar_one_or_none()
                host_name = owner.email.split("@")[0] if owner else "Host"

                await send_meeting_invites(
                    emails=invited_emails,
                    meeting_name=name,
                    join_url=join_url,
                    source_lang=source_lang,
                    target_langs=target_langs,
                    scheduled_at=scheduled_at,
                    description=description,
                    host_name=host_name,
                )
            except Exception as exc:
                log.warning("invite_emails_failed", error=str(exc))

        return meeting

    async def list_meetings(
        self, session: AsyncSession, *, user_id: uuid.UUID
    ) -> list[dict]:
        # Meetings where user is owner or participant
        stmt = (
            select(
                Meeting,
                func.count(MeetingParticipant.participant_id).label("participant_count"),
            )
            .outerjoin(MeetingParticipant, Meeting.meeting_id == MeetingParticipant.meeting_id)
            .where(
                (Meeting.owner_id == user_id)
                | (
                    Meeting.meeting_id.in_(
                        select(MeetingParticipant.meeting_id).where(
                            MeetingParticipant.user_id == user_id
                        )
                    )
                )
            )
            .group_by(Meeting.meeting_id)
            .order_by(Meeting.created_at.desc())
        )
        rows = (await session.execute(stmt)).all()

        results = []
        for meeting, pcount in rows:
            duration = None
            if meeting.started_at and meeting.ended_at:
                duration = int((meeting.ended_at - meeting.started_at).total_seconds())
            results.append({
                "meeting": meeting,
                "participant_count": pcount,
                "duration_seconds": duration,
            })
        return results

    async def get_meeting(
        self, session: AsyncSession, *, meeting_id: uuid.UUID, user_id: uuid.UUID
    ) -> Meeting:
        meeting = (
            await session.execute(
                select(Meeting).where(Meeting.meeting_id == meeting_id)
            )
        ).scalar_one_or_none()

        if meeting is None:
            raise MeetingNotFound("Meeting not found")
        return meeting

    async def join_meeting(
        self,
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
        user_id: uuid.UUID,
        display_name: str,
        language: str,
        ctx: RequestContext,
    ) -> MeetingParticipant:
        meeting = (
            await session.execute(
                select(Meeting).where(Meeting.meeting_id == meeting_id)
            )
        ).scalar_one_or_none()

        if meeting is None:
            raise MeetingNotFound("Meeting not found")
        if meeting.status == "ended":
            raise MeetingEnded("Meeting has already ended")

        # Check if already joined (idempotent)
        existing = (
            await session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.left_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if existing:
            return existing

        role = "host" if meeting.owner_id == user_id else "participant"
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=user_id,
            display_name=display_name,
            language=language,
            role=role,
        )
        session.add(participant)

        # Activate meeting if waiting
        if meeting.status == "waiting":
            meeting.status = "active"
            meeting.started_at = datetime.now(timezone.utc)

        await session.flush()

        await write_audit(
            session,
            event_category=AuditEventCategory.AI_INTERACTION,
            action=AuditAction.MEETING_JOINED,
            user_id=user_id,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            detail=f"{display_name} joined meeting",
            extra_data={"meeting_id": str(meeting_id), "language": language},
        )
        await session.commit()
        return participant

    async def end_meeting(
        self,
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
        user_id: uuid.UUID,
        ctx: RequestContext,
    ) -> Meeting:
        meeting = (
            await session.execute(
                select(Meeting).where(Meeting.meeting_id == meeting_id)
            )
        ).scalar_one_or_none()

        if meeting is None:
            raise MeetingNotFound("Meeting not found")
        if meeting.owner_id != user_id:
            raise NotAuthorized("Only the host can end the meeting")
        if meeting.status == "ended":
            return meeting

        meeting.status = "ended"
        meeting.ended_at = datetime.now(timezone.utc)

        await write_audit(
            session,
            event_category=AuditEventCategory.AI_INTERACTION,
            action=AuditAction.MEETING_ENDED,
            user_id=user_id,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            extra_data={"meeting_id": str(meeting_id)},
        )
        await session.commit()
        return meeting

    async def find_by_join_code(
        self, session: AsyncSession, *, join_code: str
    ) -> Meeting | None:
        return (
            await session.execute(
                select(Meeting).where(Meeting.join_code == join_code)
            )
        ).scalar_one_or_none()
