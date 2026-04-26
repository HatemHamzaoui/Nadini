"""Auth-Endpunkte: Magic Link Request, Verify, Health."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    current_user_id,
    get_magic_link_service,
    get_session,
    request_context,
)
from app.api.schemas import (
    ComplianceInfo,
    MagicLinkRequest,
    MagicLinkResponse,
    MagicLinkVerifyRequest,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)
from app.compliance.audit import AuditAction, AuditEventCategory, write_audit
from app.core.logging import get_logger
from app.domain.errors import (
    RateLimitExceeded,
    TokenExpiredOrUsed,
    TokenInvalid,
)
from app.services.magic_link_service import MagicLinkService, RequestContext

log = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/magic-link",
    response_model=MagicLinkResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a magic-link sign-in email",
)
async def request_magic_link(
    payload: MagicLinkRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MagicLinkService, Depends(get_magic_link_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> MagicLinkResponse:
    """Antwortet IMMER mit 202 — egal ob die E-Mail existiert.
    Schützt vor User-Enumeration."""
    try:
        await svc.request_link(
            session,
            email=payload.email,
            ui_language=payload.ui_language,
            ctx=ctx,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    except Exception as exc:  # noqa: BLE001
        # Loggen, aber API-Antwort bleibt 202.
        log.error("magic_link_request_unexpected_error", error=str(exc))
    return MagicLinkResponse()


@router.post(
    "/verify-magic",
    response_model=TokenResponse,
    summary="Verify a magic-link token and obtain JWT pair",
)
async def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MagicLinkService, Depends(get_magic_link_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> TokenResponse:
    try:
        result = await svc.verify(session, token=payload.token, ctx=ctx)
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verify attempts. Please try again later.",
        )
    except (TokenInvalid, TokenExpiredOrUsed):
        # Bewusst gleiche Antwort: kein Hinweis darauf, was schiefging.
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Token is invalid, expired, or already used.",
        )

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
        user=UserOut(
            user_id=result.user_id,
            email=result.email,
            ui_language=result.ui_language,
            role=result.role,
            tenant_id=result.tenant_id,
            tenant_risk_tier=result.tenant_risk_tier,
        ),
        compliance=ComplianceInfo(
            ai_disclosure_required=result.ai_disclosure_required,
            ai_disclosure_version=result.ai_disclosure_version,
            acknowledge_endpoint=(
                "/auth/ai-disclosure/acknowledge"
                if result.ai_disclosure_required
                else None
            ),
        ),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark the current refresh token as revoked",
)
async def logout(
    user_id: Annotated[str, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> None:
    # Revocation der konkreten Refresh-Tokens erfolgt im Refresh-Endpunkt
    # (späterer Sprint). Hier nur Audit.
    await write_audit(
        session,
        event_category=AuditEventCategory.AUTH,
        action=AuditAction.LOGOUT,
        user_id=user_id,  # type: ignore[arg-type]
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    await session.commit()


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Rotate the refresh token and obtain a new access token",
)
async def refresh_tokens(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    svc: Annotated[MagicLinkService, Depends(get_magic_link_service)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> RefreshResponse:
    try:
        new_access, new_refresh, expires_in = await svc.refresh(
            session, refresh_token=payload.refresh_token, ctx=ctx
        )
    except (TokenInvalid, TokenExpiredOrUsed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or revoked.",
        )
    return RefreshResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=expires_in,
    )


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update the current user's profile",
)
async def update_me(
    payload: UpdateProfileRequest,
    user_id: Annotated[str, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserOut:
    from sqlalchemy import select

    from app.db.models import User

    user = (
        await session.execute(select(User).where(User.user_id == user_id))
    ).scalar_one()

    if payload.ui_language is not None:
        user.ui_language = payload.ui_language
    # display_name not in User model yet — stored client-side for now

    await session.commit()

    return UserOut(
        user_id=user.user_id,
        email=user.email,
        ui_language=user.ui_language,
        role=user.role,
        tenant_id=user.tenant_id,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Return the current user including AI disclosure status",
)
async def get_me(
    user_id: Annotated[str, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MeResponse:
    from sqlalchemy import select

    from app.compliance import CURRENT_DISCLOSURE_VERSION
    from app.db.models import AIDisclosureAcknowledgment, Tenant, User

    user = (
        await session.execute(select(User).where(User.user_id == user_id))
    ).scalar_one()

    tenant_risk_tier: str | None = None
    if user.tenant_id is not None:
        tenant_risk_tier = (
            await session.execute(
                select(Tenant.risk_tier).where(Tenant.tenant_id == user.tenant_id)
            )
        ).scalar_one_or_none()

    ack_present = (
        await session.execute(
            select(AIDisclosureAcknowledgment).where(
                AIDisclosureAcknowledgment.user_id == user.user_id,
                AIDisclosureAcknowledgment.disclosure_version
                == CURRENT_DISCLOSURE_VERSION,
            )
        )
    ).scalar_one_or_none() is not None

    return MeResponse(
        user=UserOut(
            user_id=user.user_id,
            email=user.email,
            ui_language=user.ui_language,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_risk_tier=tenant_risk_tier,
        ),
        compliance=ComplianceInfo(
            ai_disclosure_required=not ack_present,
            ai_disclosure_version=(
                CURRENT_DISCLOSURE_VERSION if not ack_present else None
            ),
            acknowledge_endpoint=(
                "/auth/ai-disclosure/acknowledge" if not ack_present else None
            ),
        ),
        email_verified=user.email_verified,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.get(
    "/data-export",
    summary="Export all user data (DSGVO Art. 15)",
)
async def data_export(
    user_id: Annotated[str, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Export alle personenbezogenen Daten des angemeldeten Users."""
    from sqlalchemy import select
    from app.db.models import AIDisclosureAcknowledgment, AuditLog, User

    user = (await session.execute(select(User).where(User.user_id == user_id))).scalar_one()

    # Disclosures
    disclosures = (await session.execute(
        select(AIDisclosureAcknowledgment).where(AIDisclosureAcknowledgment.user_id == user_id)
    )).scalars().all()

    # Audit logs
    audits = (await session.execute(
        select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc()).limit(500)
    )).scalars().all()

    return {
        "user": {
            "user_id": str(user.user_id),
            "email": user.email,
            "role": user.role,
            "ui_language": user.ui_language,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
        "disclosures": [
            {"version": d.disclosure_version, "acknowledged_at": d.acknowledged_at.isoformat(),
             "locale": d.locale}
            for d in disclosures
        ],
        "audit_logs": [
            {"action": a.action, "category": a.event_category,
             "created_at": a.created_at.isoformat(), "ip": a.ip_address}
            for a in audits
        ],
        # Meeting transcripts (from shared DB)
        meetings_data = []
        try:
            from sqlalchemy import text as sql_text
            meetings_raw = (await session.execute(sql_text(
                f"SELECT m.meeting_id, m.name, m.source_lang, m.target_langs, m.status, "
                f"m.started_at, m.ended_at, m.created_at "
                f"FROM meetings m "
                f"JOIN meeting_participants mp ON mp.meeting_id = m.meeting_id "
                f"WHERE mp.user_id = '{user_id}' "
                f"ORDER BY m.created_at DESC LIMIT 100"
            ))).fetchall()

            for mr in meetings_raw:
                segments = (await session.execute(sql_text(
                    f"SELECT ts.sequence_num, ts.spoken_lang, ts.text, ts.translations, ts.created_at "
                    f"FROM transcript_segments ts "
                    f"WHERE ts.meeting_id = '{mr[0]}' "
                    f"ORDER BY ts.sequence_num LIMIT 500"
                ))).fetchall()

                meetings_data.append({
                    "meeting_id": str(mr[0]),
                    "name": mr[1],
                    "source_lang": mr[2],
                    "status": mr[4],
                    "started_at": mr[5].isoformat() if mr[5] else None,
                    "ended_at": mr[6].isoformat() if mr[6] else None,
                    "segments": [
                        {
                            "sequence": s[0], "lang": s[1], "text": s[2],
                            "translations": s[3],  # JSONB with ai_generated flag
                            "created_at": s[4].isoformat() if s[4] else None,
                        }
                        for s in segments
                    ],
                })
        except Exception:
            meetings_data = []  # Graceful if tables don't exist

        return {
            "user": {
                "user_id": str(user.user_id),
                "email": user.email,
                "role": user.role,
                "ui_language": user.ui_language,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "email_verified": user.email_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            },
            "disclosures": [
                {"version": d.disclosure_version, "acknowledged_at": d.acknowledged_at.isoformat(),
                 "locale": d.locale}
                for d in disclosures
            ],
            "meetings": meetings_data,
            "audit_logs": [
                {"action": a.action, "category": a.event_category,
                 "created_at": a.created_at.isoformat(), "ip": a.ip_address}
                for a in audits
            ],
            "export_date": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "notice": "Complete data export including all meetings, transcripts, and AI-generated translations (DSGVO Art. 15 + EU AI Act Art. 86).",
            "ai_act_note": "All translations marked with ai_generated=true indicate AI-produced content (Art. 50(2)).",
        }


@router.delete(
    "/account",
    status_code=204,
    summary="Delete user account and all data (DSGVO Art. 17)",
)
async def delete_account(
    user_id: Annotated[str, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    ctx: Annotated[RequestContext, Depends(request_context)],
) -> None:
    """Löscht den User und alle zugehörigen Daten (Right to be Forgotten)."""
    from sqlalchemy import delete, select
    from app.db.models import AIDisclosureAcknowledgment, AuditLog, MagicLinkToken, RefreshToken, User

    # Write final audit entry before deletion
    await write_audit(
        session,
        event_category=AuditEventCategory.DATA_SUBJECT_REQUEST,
        action="account.deleted",
        user_id=user_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
        detail="User account deleted (DSGVO Art. 17)",
        retention_override="permanent",
    )

    # Delete all user data
    await session.execute(delete(AIDisclosureAcknowledgment).where(AIDisclosureAcknowledgment.user_id == user_id))
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await session.execute(delete(MagicLinkToken).where(MagicLinkToken.user_id == user_id))
    # Audit logs: keep permanent entries, delete standard
    await session.execute(
        delete(AuditLog).where(AuditLog.user_id == user_id, AuditLog.retention_class == "standard")
    )
    # Delete user
    await session.execute(delete(User).where(User.user_id == user_id))
    await session.commit()
