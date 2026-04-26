"""Health Monitor — prüft Provider alle 30s, speichert Status in Redis."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.translation.base import ProviderHealth, ProviderStatus
from app.translation.registry import ProviderRegistry

log = get_logger(__name__)


class HealthMonitor:
    def __init__(self, registry: ProviderRegistry, redis: Redis, interval: int = 30) -> None:
        self._registry = registry
        self._redis = redis
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._prefix = "provider:health:"
        self._ttl = interval * 3  # stale = RED

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        log.info("health_monitor_started", interval=self._interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("health_monitor_stopped")

    async def _loop(self) -> None:
        while True:
            try:
                await self._check_all()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error("health_check_error", error=str(exc))
            await asyncio.sleep(self._interval)

    async def _check_all(self) -> None:
        for provider in self._registry.list_all():
            try:
                status = await asyncio.wait_for(provider.health_check(), timeout=5.0)
                health = ProviderHealth(
                    status=status,
                    avg_latency_ms=round(provider.get_latency_ms(), 1),
                    last_check=datetime.now(timezone.utc),
                    success_count=1,
                )
            except asyncio.TimeoutError:
                health = ProviderHealth(
                    status=ProviderStatus.RED,
                    last_check=datetime.now(timezone.utc),
                    error_count=1,
                    last_error="health_check_timeout",
                )
            except Exception as exc:
                health = ProviderHealth(
                    status=ProviderStatus.RED,
                    last_check=datetime.now(timezone.utc),
                    error_count=1,
                    last_error=str(exc),
                )

            # Store in Redis
            key = f"{self._prefix}{provider.name}"
            data = {
                "status": health.status.value,
                "avg_latency_ms": health.avg_latency_ms,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "error_count": health.error_count,
                "success_count": health.success_count,
                "last_error": health.last_error,
            }
            await self._redis.setex(key, self._ttl, json.dumps(data))

    async def get_health(self, name: str) -> ProviderHealth:
        key = f"{self._prefix}{name}"
        raw = await self._redis.get(key)
        if not raw:
            return ProviderHealth(status=ProviderStatus.RED)
        data = json.loads(raw)
        return ProviderHealth(
            status=ProviderStatus(data.get("status", "red")),
            avg_latency_ms=data.get("avg_latency_ms", 0),
            last_check=datetime.fromisoformat(data["last_check"]) if data.get("last_check") else None,
            error_count=data.get("error_count", 0),
            success_count=data.get("success_count", 0),
            last_error=data.get("last_error"),
        )

    async def get_all_health(self) -> dict[str, ProviderHealth]:
        result = {}
        for provider in self._registry.list_all():
            result[provider.name] = await self.get_health(provider.name)
        return result
