"""Audit-Logging für den Meeting-Service (schreibt in shared audit_logs Tabelle)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditEventCategory:
    AI_INTERACTION = "ai_interaction"
    COMPLIANCE = "compliance"


class AuditAction:
    MEETING_CREATED = "meeting.created"
    MEETING_JOINED = "meeting.joined"
    MEETING_ENDED = "meeting.ended"
    MEETING_LEFT = "meeting.left"
    TRANSCRIPT_SEGMENT = "meeting.transcript_segment"


async def write_audit(
    session: AsyncSession,
    *,
    event_category: str,
    action: str,
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    detail: str | None = None,
    extra_data: dict | None = None,
    retention_class: str = "standard",
) -> None:
    log = AuditLog(
        event_category=event_category,
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        ip_address=ip_address,
        user_agent=user_agent,
        detail=detail,
        extra_data=extra_data,
        retention_class=retention_class,
    )
    session.add(log)
