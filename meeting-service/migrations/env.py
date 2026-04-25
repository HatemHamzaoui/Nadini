"""Alembic env.py — async migration runner for meeting-service."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

db_url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


VERSION_TABLE = "alembic_version_meeting"


def run_migrations_offline() -> None:
    context.configure(url=db_url, target_metadata=target_metadata, literal_binds=True, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(db_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
