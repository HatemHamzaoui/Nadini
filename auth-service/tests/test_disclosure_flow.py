"""Tests für den AI-Disclosure-Flow (Art. 50(1)+(5) AI Act)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.compliance import CURRENT_DISCLOSURE_VERSION
from app.db.models import AIDisclosureAcknowledgment, AuditLog, User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Hilfsfunktion: vollständig einloggen → Bearer-Token
# ---------------------------------------------------------------------------


async def _login_and_get_access_token(
    client: AsyncClient, email: str, captured_tokens: list[str]
) -> str:
    await client.post("/auth/magic-link", json={"email": email, "ui_language": "de"})
    token = captured_tokens[-1]
    r = await client.post("/auth/verify-magic", json={"token": token})
    assert r.status_code == 200
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests: GET /auth/ai-disclosure
# ---------------------------------------------------------------------------


async def test_get_disclosure_default_locale_en(client: AsyncClient) -> None:
    r = await client.get("/auth/ai-disclosure")
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "en"
    assert body["version"] == CURRENT_DISCLOSURE_VERSION
    assert "title" in body and "body" in body
    assert "AI" in body["title"] or "ai" in body["title"].lower()


async def test_get_disclosure_german(client: AsyncClient) -> None:
    r = await client.get("/auth/ai-disclosure?locale=de")
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "de"
    assert "KI" in body["title"]


async def test_get_disclosure_unknown_locale_falls_back_to_en(
    client: AsyncClient,
) -> None:
    r = await client.get("/auth/ai-disclosure?locale=xx")
    assert r.status_code == 200
    assert r.json()["locale"] == "en"


async def test_list_locales(client: AsyncClient) -> None:
    r = await client.get("/auth/ai-disclosure/locales")
    assert r.status_code == 200
    locales = r.json()["locales"]
    assert "de" in locales and "en" in locales and "fr" in locales


# ---------------------------------------------------------------------------
# Tests: POST /auth/ai-disclosure/acknowledge
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_tokens(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    captured: list[str] = []
    from app.services import magic_link_service as mls
    original = mls.generate_token

    def _spy(byte_length: int = 32) -> str:
        token = original(byte_length)
        captured.append(token)
        return token

    monkeypatch.setattr(mls, "generate_token", _spy)
    return captured


async def test_acknowledge_disclosure_persists_record(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    access = await _login_and_get_access_token(
        client, "ack@example.com", captured_tokens
    )

    r = await client.post(
        "/auth/ai-disclosure/acknowledge",
        json={"version": CURRENT_DISCLOSURE_VERSION, "locale": "de"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 201
    assert r.json() == {"acknowledged": True, "version": CURRENT_DISCLOSURE_VERSION}

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (
            await s.execute(select(User).where(User.email == "ack@example.com"))
        ).scalar_one()
        record = (
            await s.execute(
                select(AIDisclosureAcknowledgment).where(
                    AIDisclosureAcknowledgment.user_id == user.user_id
                )
            )
        ).scalar_one()
        assert record.disclosure_version == CURRENT_DISCLOSURE_VERSION
        assert record.locale == "de"


async def test_acknowledge_is_idempotent(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    access = await _login_and_get_access_token(
        client, "idem@example.com", captured_tokens
    )

    r1 = await client.post(
        "/auth/ai-disclosure/acknowledge",
        json={"version": CURRENT_DISCLOSURE_VERSION, "locale": "en"},
        headers={"Authorization": f"Bearer {access}"},
    )
    r2 = await client.post(
        "/auth/ai-disclosure/acknowledge",
        json={"version": CURRENT_DISCLOSURE_VERSION, "locale": "en"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (
            await s.execute(select(User).where(User.email == "idem@example.com"))
        ).scalar_one()
        records = (
            await s.execute(
                select(AIDisclosureAcknowledgment).where(
                    AIDisclosureAcknowledgment.user_id == user.user_id
                )
            )
        ).all()
        assert len(records) == 1


async def test_acknowledge_writes_compliance_audit_log_with_permanent_retention(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    access = await _login_and_get_access_token(
        client, "audit-comp@example.com", captured_tokens
    )

    r = await client.post(
        "/auth/ai-disclosure/acknowledge",
        json={"version": CURRENT_DISCLOSURE_VERSION},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 201

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (
            await s.execute(select(User).where(User.email == "audit-comp@example.com"))
        ).scalar_one()
        logs = (
            await s.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user.user_id)
                .where(AuditLog.action == "compliance.disclosure_acknowledged")
            )
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].event_category == "compliance"
        assert logs[0].retention_class == "permanent"


async def test_acknowledge_requires_authentication(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/ai-disclosure/acknowledge",
        json={"version": CURRENT_DISCLOSURE_VERSION},
    )
    assert r.status_code == 401


async def test_login_after_acknowledge_no_longer_requires_disclosure(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    """Nach Bestätigung muss ``ai_disclosure_required`` beim erneuten Login false sein."""
    email = "second-login@example.com"
    access1 = await _login_and_get_access_token(client, email, captured_tokens)
    await client.post(
        "/auth/ai-disclosure/acknowledge",
        json={"version": CURRENT_DISCLOSURE_VERSION},
        headers={"Authorization": f"Bearer {access1}"},
    )

    # Zweiter Login
    await client.post("/auth/magic-link", json={"email": email})
    token = captured_tokens[-1]
    r = await client.post("/auth/verify-magic", json={"token": token})
    assert r.status_code == 200
    body = r.json()
    assert body["compliance"]["ai_disclosure_required"] is False
    assert body["compliance"]["ai_disclosure_version"] is None
