"""Compliance-Endpunkte: AI-Disclosure (Art. 50(1)+(5) AI Act).

Wird auch im Frontend als Pflicht-Schritt gerendert, sobald
``compliance.ai_disclosure_required == true`` in der Login-Antwort steht.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, get_magic_link_service, get_session, request_context
from app.api.schemas import (
    DisclosureAcknowledgeRequest,
    DisclosureAcknowledgeResponse,
    DisclosureTextOut,
)
from app.compliance import (
    CURRENT_DISCLOSURE_VERSION,
    DISCLOSURE_TEXTS,
    get_disclosure_text,
)
from app.services.magic_link_service import MagicLinkService, RequestContext

router = APIRouter(prefix="/auth/ai-disclosure", tags=["compliance"])


@router.get(
    "",
    response_model=DisclosureTextOut,
    summary="Get the current AI Act Art. 50 disclosure text",
)
async def get_current_disclosure(
    locale: Annotated[str, Query(min_length=2, max_length=10)] = "en",
) -> DisclosureTextOut:
    text = get_disclosure_text(locale)
    return DisclosureTextOut(
        version=text.version,
        locale=text.locale,
        title=text.title,
        body=text.body,
        short_label=text.short_label,
        acknowledge_button=text.acknowledge_button,
    )


@router.get(
    "/locales",
    summary="List available disclosure locales",
)
async def list_locales() -> dict[str, list[str]]:
    return {"locales": sorted(DISCLOSURE_TEXTS.keys())}


@router.post(
    "/acknowledge",
    response_model=DisclosureAcknowledgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record that the user has acknowledged the AI disclosure",
)
async def acknowledge_disclosure(
    payload: DisclosureAcknowledgeRequest,
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MagicLinkService, Depends(get_magic_link_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> DisclosureAcknowledgeResponse:
    # Wir akzeptieren ausschließlich die *aktuelle* Disclosure-Version.
    # Damit ist sichergestellt, dass User immer auf den jüngsten Stand bestätigt haben.
    version = (
        payload.version
        if payload.version == CURRENT_DISCLOSURE_VERSION
        else CURRENT_DISCLOSURE_VERSION
    )
    await svc.acknowledge_disclosure(
        session,
        user_id=user_id,
        version=version,
        ctx=ctx,
        locale=payload.locale,
    )
    return DisclosureAcknowledgeResponse(version=version)
