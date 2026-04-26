"""Serious Incident Management — EU AI Act Art. 73.

72h notification requirement for serious incidents.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, get_session, require_admin, state
from app.db.models import SeriousIncident

router = APIRouter(prefix="/incidents", tags=["compliance"], redirect_slashes=False)


@router.post("", status_code=201, summary="Report a serious incident (Art. 73)")
async def report_incident(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    incident = SeriousIncident(
        reported_by=user_id,
        tenant_id=uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None,
        category=body.get("category", "functionality"),
        severity=body.get("severity", "medium"),
        title=body.get("title", "Untitled incident"),
        description=body.get("description", ""),
        affected_users_count=body.get("affected_users_count"),
    )
    session.add(incident)
    await session.commit()

    # Calculate 72h deadline
    deadline = datetime(incident.created_at.year, incident.created_at.month,
                        incident.created_at.day, tzinfo=timezone.utc)

    return {
        "incident_id": str(incident.incident_id),
        "status": incident.status,
        "severity": incident.severity,
        "created_at": incident.created_at.isoformat(),
        "authority_notification_deadline": "72 hours from creation",
        "note": "Art. 73 EU AI Act: serious incidents must be reported to authorities within 72 hours.",
    }


@router.get("", summary="List all incidents (admin)")
async def list_incidents(
    user_id: Annotated[uuid.UUID, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    incidents = (await session.execute(
        select(SeriousIncident).order_by(SeriousIncident.created_at.desc())
    )).scalars().all()

    return [
        {
            "incident_id": str(i.incident_id),
            "category": i.category,
            "severity": i.severity,
            "title": i.title,
            "status": i.status,
            "authority_notified": i.authority_notified,
            "created_at": i.created_at.isoformat(),
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        }
        for i in incidents
    ]


@router.get("/{incident_id}", summary="Get incident details")
async def get_incident(
    incident_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    incident = (await session.execute(
        select(SeriousIncident).where(SeriousIncident.incident_id == incident_id)
    )).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return {
        "incident_id": str(incident.incident_id),
        "category": incident.category,
        "severity": incident.severity,
        "title": incident.title,
        "description": incident.description,
        "affected_users_count": incident.affected_users_count,
        "root_cause": incident.root_cause,
        "remediation_steps": incident.remediation_steps,
        "status": incident.status,
        "authority_notified": incident.authority_notified,
        "authority_notified_at": incident.authority_notified_at.isoformat() if incident.authority_notified_at else None,
        "authority_reference": incident.authority_reference,
        "created_at": incident.created_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


@router.put("/{incident_id}", summary="Update incident (admin)")
async def update_incident(
    incident_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    incident = (await session.execute(
        select(SeriousIncident).where(SeriousIncident.incident_id == incident_id)
    )).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if "status" in body:
        incident.status = body["status"]
        if body["status"] == "resolved":
            incident.resolved_at = datetime.now(timezone.utc)
    if "root_cause" in body:
        incident.root_cause = body["root_cause"]
    if "remediation_steps" in body:
        incident.remediation_steps = body["remediation_steps"]
    if "authority_notified" in body and body["authority_notified"]:
        incident.authority_notified = True
        incident.authority_notified_at = datetime.now(timezone.utc)
    if "authority_reference" in body:
        incident.authority_reference = body["authority_reference"]

    await session.commit()
    return {"status": "updated", "incident_id": str(incident_id), "incident_status": incident.status}
