"""Provider-Management Admin API."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, get_session, require_admin, state
from app.db.models import LanguageRoute, ProviderConfig

router = APIRouter(prefix="/providers", tags=["providers"], redirect_slashes=False)


@router.get("", summary="List all providers with health status")
async def list_providers(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    configs = (await session.execute(
        select(ProviderConfig).order_by(ProviderConfig.priority)
    )).scalars().all()

    result = []
    for cfg in configs:
        health_data = {"status": "unknown", "avg_latency_ms": 0}
        if state.health_monitor:
            h = await state.health_monitor.get_health(cfg.name)
            health_data = {
                "status": h.status.value,
                "avg_latency_ms": h.avg_latency_ms,
                "last_check": h.last_check.isoformat() if h.last_check else None,
                "last_error": h.last_error,
            }

        result.append({
            "provider_id": str(cfg.provider_id),
            "name": cfg.name,
            "provider_type": cfg.provider_type,
            "enabled": cfg.enabled,
            "priority": cfg.priority,
            "supported_pairs": cfg.supported_pairs,
            "has_key": bool(cfg.api_key),
            "health": health_data,
        })
    return result


@router.get("/health", summary="Health dashboard")
async def health_dashboard(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
) -> dict:
    if not state.health_monitor:
        return {"providers": []}
    all_health = await state.health_monitor.get_all_health()
    return {
        "providers": [
            {"name": name, "status": h.status.value, "latency_ms": h.avg_latency_ms,
             "last_check": h.last_check.isoformat() if h.last_check else None}
            for name, h in all_health.items()
        ]
    }


@router.put("/{provider_id}", summary="Update provider config")
async def update_provider(
    provider_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    cfg = (await session.execute(
        select(ProviderConfig).where(ProviderConfig.provider_id == provider_id)
    )).scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Provider not found")

    if "enabled" in body:
        cfg.enabled = body["enabled"]
    if "priority" in body:
        cfg.priority = body["priority"]
    if "api_url" in body:
        cfg.api_url = body["api_url"]
    if "api_key" in body:
        cfg.api_key = body["api_key"]  # Store key in DB
    if "config_extra" in body:
        cfg.config_extra = body["config_extra"]  # For Papago client_id/secret etc.

    await session.commit()

    # Reload provider with new key
    if state.provider_registry and ("api_key" in body or "enabled" in body):
        async with state.session_factory() as reload_session:
            await state.provider_registry.load_from_db(reload_session)
            if state.translation_router:
                await state.translation_router.load_routes(reload_session)

    return {"status": "updated", "name": cfg.name, "enabled": cfg.enabled, "has_key": bool(cfg.api_key)}


@router.get("/routes", summary="List language routes")
async def list_routes(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    routes = (await session.execute(select(LanguageRoute))).scalars().all()
    configs = {c.provider_id: c.name for c in (await session.execute(select(ProviderConfig))).scalars().all()}

    result = []
    for r in routes:
        primary_name = configs.get(r.primary_provider_id, "?")
        backup_name = configs.get(r.backup_provider_id, "?")

        primary_health = {"status": "unknown"}
        backup_health = {"status": "unknown"}
        if state.health_monitor:
            ph = await state.health_monitor.get_health(primary_name)
            bh = await state.health_monitor.get_health(backup_name)
            primary_health = {"status": ph.status.value, "latency_ms": ph.avg_latency_ms}
            backup_health = {"status": bh.status.value, "latency_ms": bh.avg_latency_ms}

        result.append({
            "source_lang": r.source_lang,
            "target_lang": r.target_lang,
            "primary": {"name": primary_name, "health": primary_health},
            "backup": {"name": backup_name, "health": backup_health},
        })
    return result


@router.put("/routes/{source_lang}/{target_lang}", summary="Set routing for language pair")
async def set_route(
    source_lang: str,
    target_lang: str,
    user_id: Annotated[uuid.UUID, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    primary_id = body.get("primary_provider_id")
    backup_id = body.get("backup_provider_id")
    if not primary_id or not backup_id:
        raise HTTPException(status_code=400, detail="primary_provider_id and backup_provider_id required")

    route = (await session.execute(
        select(LanguageRoute).where(
            LanguageRoute.source_lang == source_lang,
            LanguageRoute.target_lang == target_lang,
        )
    )).scalar_one_or_none()

    if route:
        route.primary_provider_id = uuid.UUID(primary_id)
        route.backup_provider_id = uuid.UUID(backup_id)
    else:
        route = LanguageRoute(
            source_lang=source_lang,
            target_lang=target_lang,
            primary_provider_id=uuid.UUID(primary_id),
            backup_provider_id=uuid.UUID(backup_id),
        )
        session.add(route)

    await session.commit()

    # Refresh router cache
    if state.translation_router:
        await state.translation_router.load_routes(session)

    return {"status": "updated", "source_lang": source_lang, "target_lang": target_lang}


@router.post("/{provider_id}/test", summary="Test provider with sample text")
async def test_provider(
    provider_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict,
) -> dict:
    cfg = (await session.execute(
        select(ProviderConfig).where(ProviderConfig.provider_id == provider_id)
    )).scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = state.provider_registry.get(cfg.name) if state.provider_registry else None
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not loaded")

    text = body.get("text", "Hallo Welt")
    src = body.get("source_lang", "de")
    tgt = body.get("target_lang", "en")

    try:
        translated, latency = await provider.timed_translate(text, src, tgt)
        return {"translated_text": translated, "latency_ms": round(latency, 1), "status": "ok", "provider": cfg.name}
    except Exception as exc:
        return {"translated_text": None, "latency_ms": 0, "status": "error", "error": str(exc), "provider": cfg.name}


@router.get("/quality", summary="Quality monitoring dashboard")
async def quality_dashboard(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
) -> dict:
    if not state.quality_monitor:
        return {"latency": {}, "feedback": {}, "anomalies": []}
    return state.quality_monitor.get_dashboard()


@router.post("/quality/feedback", summary="Submit translation quality feedback")
async def submit_feedback(
    user_id: Annotated[uuid.UUID, Depends(current_user_id)],
    body: dict,
) -> dict:
    if not state.quality_monitor:
        return {"status": "not_available"}

    from app.translation.quality import FeedbackEntry
    feedback = FeedbackEntry(
        segment_id=body.get("segment_id", ""),
        meeting_id=body.get("meeting_id", ""),
        user_id=str(user_id),
        provider=body.get("provider", ""),
        source_lang=body.get("source_lang", ""),
        target_lang=body.get("target_lang", ""),
        rating=body.get("rating", 3),
    )
    await state.quality_monitor.record_feedback(feedback)
    return {"status": "recorded", "rating": feedback.rating}
