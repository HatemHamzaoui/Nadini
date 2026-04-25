"""Test-Fixtures: hochgefahrene Postgres + Redis via testcontainers."""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def jwt_keys() -> Iterator[tuple[Path, Path]]:
    """Erzeugt einmal pro Testlauf ein RS256-Schlüsselpaar."""
    with tempfile.TemporaryDirectory() as tmp:
        priv = Path(tmp) / "priv.pem"
        pub = Path(tmp) / "pub.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(priv),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "rsa", "-pubout", "-in", str(priv), "-out", str(pub)],
            check=True,
            capture_output=True,
        )
        yield priv, pub


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16") as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer("redis:7-alpine") as r:
        yield r


@pytest.fixture(scope="session")
def configure_env(
    postgres_container: PostgresContainer,
    redis_container: RedisContainer,
    jwt_keys: tuple[Path, Path],
) -> Iterator[None]:
    priv, pub = jwt_keys
    db_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    ).replace("postgresql://", "postgresql+asyncpg://")
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)

    env = {
        "DATABASE_URL": db_url,
        "REDIS_URL": f"redis://{redis_host}:{redis_port}/0",
        "JWT_PRIVATE_KEY_PATH": str(priv),
        "JWT_PUBLIC_KEY_PATH": str(pub),
        "JWT_ISSUER": "http://test",
        "JWT_AUDIENCE": "nadini-test",
        "MAGIC_LINK_BASE_URL": "http://test",
        "MAILER_DRIVER": "console",
        "MAIL_FROM": "test@test.local",
        "MAIL_FROM_NAME": "Test",
        "CORS_ORIGINS": "http://localhost",
        "APP_ENV": "development",
        "LOG_FORMAT": "console",
        # Schnellere Limits für Tests
        "MAGIC_LINK_RATE_PER_EMAIL": "3",
        "MAGIC_LINK_RATE_PER_IP": "10",
        "MAGIC_LINK_VERIFY_RATE_PER_IP": "10",
        "MAGIC_LINK_RATE_WINDOW_SECONDS": "60",
    }
    for k, v in env.items():
        os.environ[k] = v

    # Settings-Cache leeren
    from app.core.config import get_settings
    get_settings.cache_clear()

    yield


@pytest_asyncio.fixture(scope="session")
async def engine(configure_env: None) -> AsyncIterator[AsyncEngine]:
    from app.core.config import get_settings
    settings = get_settings()
    eng = create_async_engine(settings.database_url, pool_pre_ping=True)

    # Migrationen laufen lassen
    proc = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ},
    )
    if proc.returncode != 0:
        raise RuntimeError(f"alembic failed: {proc.stderr}")

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """Erzeugt eine ASGI-Client-Instanz mit hochgefahrenem App-Lifespan."""
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Lifespan manuell triggern
        async with app.router.lifespan_context(app):
            yield ac


@pytest_asyncio.fixture
async def clean_redis() -> AsyncIterator[None]:
    """Leert Redis vor jedem Test, damit Rate-Limits nicht durchschlagen."""
    from app.core.config import get_settings
    settings = get_settings()
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    await r.flushdb()
    yield
    await r.aclose()
