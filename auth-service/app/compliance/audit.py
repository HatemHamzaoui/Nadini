"""Audit-Logging-Wrapper.

Stellt eine semantische API bereit, damit Audit-Events konsistent kategorisiert
werden — kritisch für AI-Act-konformes Logging (Art. 12 + 26).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.risk_tier import retention_class_for
from app.db.models import AuditLog


class AuditEventCategory:
    AUTH = "auth"
    AI_INTERACTION = "ai_interaction"
    COMPLIANCE = "compliance"
    ADMIN = "admin"
    DATA_SUBJECT_REQUEST = "data_subject_request"


class AuditAction:
    # Auth
    MAGIC_LINK_REQUESTED = "magic_link.requested"
    MAGIC_LINK_VERIFIED = "magic_link.verified"
    MAGIC_LINK_FAILED = "magic_link.failed"
    LOGOUT = "auth.logout"
    REFRESH = "auth.refresh"

    # Compliance
    AI_DISCLOSURE_SHOWN = "compliance.disclosure_shown"
    AI_DISCLOSURE_ACKNOWLEDGED = "compliance.disclosure_acknowledged"
    AI_DISCLOSURE_VERSION_BUMP = "compliance.disclosure_version_bump"

    # Data subject (DSGVO + AI Act Art. 86)
    DATA_EXPORT_REQUESTED = "dsr.export_requested"
    DATA_DELETION_REQUESTED = "dsr.deletion_requested"


async def write_audit(
    session: AsyncSession,
    *,
    event_category: str,
    action: str,
    user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    tenant_risk_tier: str | None = None,
    detail: str | None = None,
    ai_model_used: str | None = None,
    extra_data: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    retention_override: str | None = None,
) -> None:
    """Schreibt einen Audit-Eintrag. Wählt die Retention-Klasse automatisch
    anhand des Tenant-Risk-Tiers (kann durch ``retention_override`` übersteuert
    werden, z. B. für ``permanent`` bei DSR-Anfragen)."""
    retention = retention_override or retention_class_for(tenant_risk_tier)
    entry = AuditLog(
        event_category=event_category,
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        detail=detail,
        ai_model_used=ai_model_used,
        extra_data=extra_data,
        ip_address=ip_address,
        user_agent=user_agent,
        retention_class=retention,
    )
    session.add(entry)
    # Commit übernimmt der Aufrufer (in der Regel innerhalb einer Transaktion).
