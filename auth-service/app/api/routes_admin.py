"""Admin-API: User- und Tenant-Verwaltung (nur für admin-Rolle)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, current_user_id
from app.api.schemas import UserOut
from app.core.jwt import JWTIssuer
from app.core.logging import get_logger
from app.db.models import Tenant, User

log = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_ROLES = {"guest", "user", "moderator", "interpreter", "tenant_admin", "admin"}


async def require_admin_role(
    authorization: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    """Verify JWT and require admin role."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    token = authorization.split(" ", 1)[1].strip()

    from app.api.deps import state
    jwt = state.jwt_issuer
    if not jwt:
        raise HTTPException(status_code=500, detail="JWT issuer not initialized.")

    try:
        claims = jwt.decode(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    if claims.get("typ") != "access":
        raise HTTPException(status_code=401, detail="Wrong token type.")
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required.")

    return uuid.UUID(claims["sub"])


@router.get("/users", summary="List all users (admin only)")
async def list_users(
    admin_id: Annotated[uuid.UUID, Depends(require_admin_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    users = (await session.execute(
        select(User).order_by(User.created_at.desc())
    )).scalars().all()

    return [
        {
            "user_id": str(u.user_id),
            "email": u.email,
            "role": u.role,
            "ui_language": u.ui_language,
            "tenant_id": str(u.tenant_id) if u.tenant_id else None,
            "email_verified": u.email_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]


@router.put("/users/{user_id}/role", summary="Change user role (admin only)")
async def set_user_role(
    user_id: uuid.UUID,
    admin_id: Annotated[uuid.UUID, Depends(require_admin_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    new_role = body.get("role", "").strip()
    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")

    user = (await session.execute(
        select(User).where(User.user_id == user_id)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    user.role = new_role
    await session.commit()

    log.info("user_role_changed", user_id=str(user_id), old_role=old_role, new_role=new_role, by=str(admin_id))
    return {"user_id": str(user_id), "email": user.email, "old_role": old_role, "new_role": new_role}


@router.get("/tenants", summary="List all tenants (admin only)")
async def list_tenants(
    admin_id: Annotated[uuid.UUID, Depends(require_admin_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    tenants = (await session.execute(
        select(Tenant).order_by(Tenant.created_at.desc())
    )).scalars().all()

    return [
        {
            "tenant_id": str(t.tenant_id),
            "name": t.name,
            "legal_entity": t.legal_entity,
            "risk_tier": t.risk_tier,
            "country_code": t.country_code,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tenants
    ]


@router.post("/tenants", summary="Create a new tenant (admin only)", status_code=201)
async def create_tenant(
    admin_id: Annotated[uuid.UUID, Depends(require_admin_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tenant name required")

    tenant = Tenant(
        name=name,
        legal_entity=body.get("legal_entity"),
        country_code=body.get("country_code", "DE"),
        risk_tier=body.get("risk_tier", "standard"),
    )
    session.add(tenant)
    await session.commit()

    log.info("tenant_created", tenant_id=str(tenant.tenant_id), name=name, by=str(admin_id))
    return {"tenant_id": str(tenant.tenant_id), "name": name, "risk_tier": tenant.risk_tier}


@router.get("/stats", summary="Platform statistics (admin only)")
async def admin_stats(
    admin_id: Annotated[uuid.UUID, Depends(require_admin_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    user_count = (await session.execute(select(func.count(User.user_id)))).scalar_one()
    tenant_count = (await session.execute(select(func.count(Tenant.tenant_id)))).scalar_one()

    # Role distribution
    role_counts = (await session.execute(
        select(User.role, func.count(User.user_id)).group_by(User.role)
    )).all()

    return {
        "users": user_count,
        "tenants": tenant_count,
        "roles": {role: count for role, count in role_counts},
    }
