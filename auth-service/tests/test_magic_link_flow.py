"""End-to-End-Tests für den Magic-Link-Flow.

Setup: testcontainers (Postgres + Redis), echter ASGI-Client.
Mailer ist auf 'console' — Token wird direkt aus der DB gelesen.
"""
from __future__ import annotations

import asyncio
import hashlib

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.db.models import (
    AIDisclosureAcknowledgment,
    AuditLog,
    MagicLinkToken,
    RefreshToken,
    User,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


async def _read_latest_token_for(engine: AsyncEngine, email: str) -> str:
    """Liest den jüngsten Token-Hash aus der DB. Da wir den Klartext nicht haben,
    erzeugen wir den Token im Test selbst und vergleichen den Hash.

    Trick: Wir patchen ``generate_token`` nicht — stattdessen lesen wir den
    aktuellen Hash, generieren in einer Schleife Klartext-Token und brechen ab,
    sobald der Hash übereinstimmt. Das ist nur in Tests sinnvoll, weil der
    Suchraum riesig ist. → Wir verwenden stattdessen einen Monkeypatch-Ansatz
    in den Tests, die Klartext-Token brauchen.
    """
    raise NotImplementedError("Use _capture_token via monkeypatch instead.")


def _captured_token_holder() -> dict[str, str]:
    """Gemeinsamer Container für den durch Monkeypatch abgefangenen Token."""
    return {}


# ---------------------------------------------------------------------------
# Tests: Request
# ---------------------------------------------------------------------------


async def test_request_magic_link_returns_202_for_new_email(
    client: AsyncClient, clean_redis: None
) -> None:
    resp = await client.post(
        "/auth/magic-link",
        json={"email": "alice@example.com", "ui_language": "de"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "message" in body


async def test_request_magic_link_returns_202_for_unknown_email_too(
    client: AsyncClient, clean_redis: None
) -> None:
    """Anti-User-Enumeration: Antwort muss identisch sein."""
    r1 = await client.post(
        "/auth/magic-link", json={"email": "knownuser@example.com"}
    )
    r2 = await client.post(
        "/auth/magic-link", json={"email": "ghost-9384@example.com"}
    )
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json() == r2.json()


async def test_request_magic_link_creates_user_and_token(
    client: AsyncClient, engine: AsyncEngine, clean_redis: None
) -> None:
    email = "create-me@example.com"
    resp = await client.post("/auth/magic-link", json={"email": email})
    assert resp.status_code == 202

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (
            await s.execute(select(User).where(User.email == email))
        ).scalar_one()
        assert user.email_verified is False
        token_count = (
            await s.execute(
                select(MagicLinkToken).where(MagicLinkToken.user_id == user.user_id)
            )
        ).all()
        assert len(token_count) == 1


async def test_request_magic_link_invalid_email_returns_422(
    client: AsyncClient, clean_redis: None
) -> None:
    resp = await client.post("/auth/magic-link", json={"email": "not-an-email"})
    assert resp.status_code == 422


async def test_request_magic_link_rate_limit_per_email(
    client: AsyncClient, clean_redis: None
) -> None:
    """Settings: MAGIC_LINK_RATE_PER_EMAIL=3 — der vierte Aufruf muss 429 liefern."""
    email = "rate-email@example.com"
    for _ in range(3):
        r = await client.post("/auth/magic-link", json={"email": email})
        assert r.status_code == 202

    r = await client.post("/auth/magic-link", json={"email": email})
    assert r.status_code == 429


# ---------------------------------------------------------------------------
# Tests: Verify (mit Token-Capture per Monkeypatch)
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_tokens(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Fängt jeden in MagicLinkService.generate_token erzeugten Klartext-Token ab."""
    captured: list[str] = []

    from app.services import magic_link_service as mls

    original = mls.generate_token

    def _spy(byte_length: int = 32) -> str:
        token = original(byte_length)
        captured.append(token)
        return token

    monkeypatch.setattr(mls, "generate_token", _spy)
    return captured


async def test_verify_with_valid_token_returns_jwt_pair(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    email = "verify-ok@example.com"
    r = await client.post("/auth/magic-link", json={"email": email, "ui_language": "de"})
    assert r.status_code == 202
    assert len(captured_tokens) == 1
    token = captured_tokens[0]

    r = await client.post("/auth/verify-magic", json={"token": token})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == email
    assert body["user"]["ui_language"] == "de"
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["compliance"]["ai_disclosure_required"] is True
    assert body["compliance"]["ai_disclosure_version"] is not None


async def test_verify_marks_token_as_used(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    await client.post("/auth/magic-link", json={"email": "used@example.com"})
    token = captured_tokens[0]
    await client.post("/auth/verify-magic", json={"token": token})

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        token_hash = hashlib.sha256(token.encode()).digest()
        row = (
            await s.execute(
                select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash)
            )
        ).scalar_one()
        assert row.used_at is not None


async def test_verify_with_already_used_token_returns_410(
    client: AsyncClient, clean_redis: None, captured_tokens: list[str]
) -> None:
    await client.post("/auth/magic-link", json={"email": "double@example.com"})
    token = captured_tokens[0]

    r1 = await client.post("/auth/verify-magic", json={"token": token})
    assert r1.status_code == 200

    r2 = await client.post("/auth/verify-magic", json={"token": token})
    assert r2.status_code == 410


async def test_verify_with_unknown_token_returns_410(
    client: AsyncClient, clean_redis: None
) -> None:
    fake_token = "a" * 43
    r = await client.post("/auth/verify-magic", json={"token": fake_token})
    assert r.status_code == 410


async def test_verify_with_malformed_token_returns_422(
    client: AsyncClient, clean_redis: None
) -> None:
    r = await client.post("/auth/verify-magic", json={"token": "short"})
    assert r.status_code == 422  # Pydantic-Validation


async def test_verify_with_expired_token_returns_410(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    await client.post("/auth/magic-link", json={"email": "expired@example.com"})
    token = captured_tokens[0]

    # Token künstlich ablaufen lassen
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        await s.execute(
            text(
                "UPDATE magic_link_tokens "
                "SET expires_at = now() - interval '1 hour' "
                "WHERE token_hash = :h"
            ),
            {"h": hashlib.sha256(token.encode()).digest()},
        )
        await s.commit()

    r = await client.post("/auth/verify-magic", json={"token": token})
    assert r.status_code == 410


async def test_verify_creates_refresh_token_record(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    email = "refresh-record@example.com"
    await client.post("/auth/magic-link", json={"email": email})
    token = captured_tokens[0]
    await client.post("/auth/verify-magic", json={"token": token})

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalar_one()
        rts = (
            await s.execute(
                select(RefreshToken).where(RefreshToken.user_id == user.user_id)
            )
        ).all()
        assert len(rts) == 1


async def test_verify_marks_email_verified(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
    captured_tokens: list[str],
) -> None:
    email = "verify-flag@example.com"
    await client.post("/auth/magic-link", json={"email": email})
    await client.post("/auth/verify-magic", json={"token": captured_tokens[0]})

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalar_one()
        assert user.email_verified is True
        assert user.last_login_at is not None


# ---------------------------------------------------------------------------
# Tests: Audit-Log
# ---------------------------------------------------------------------------


async def test_audit_log_for_magic_link_request(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
) -> None:
    email = "audit-req@example.com"
    await client.post("/auth/magic-link", json={"email": email})

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalar_one()
        logs = (
            await s.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user.user_id)
                .where(AuditLog.action == "magic_link.requested")
            )
        ).all()
        assert len(logs) == 1


async def test_audit_log_for_failed_verify(
    client: AsyncClient,
    engine: AsyncEngine,
    clean_redis: None,
) -> None:
    fake = "x" * 43
    await client.post("/auth/verify-magic", json={"token": fake})

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        logs = (
            await s.execute(
                select(AuditLog).where(AuditLog.action == "magic_link.failed")
            )
        ).all()
        assert len(logs) >= 1
