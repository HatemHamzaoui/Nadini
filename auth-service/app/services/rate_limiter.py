"""Sliding-Window Rate Limiter über Redis.

Verwendet einen sortierten Set pro Bucket und entfernt Einträge außerhalb
des Fensters bei jedem Aufruf.
"""
from __future__ import annotations

import time
import uuid
from typing import Protocol

from redis.asyncio import Redis


class RateLimiter(Protocol):
    async def hit(self, bucket_key: str, limit: int, window_seconds: int) -> bool:
        """Returns True wenn der Aufruf erlaubt ist, False wenn das Limit überschritten."""
        ...


class RedisRateLimiter:
    """Sliding Window über ZSET in Redis.

    Algorithmus:
    1. Entferne alle Einträge älter als window_seconds.
    2. Zähle verbleibende Einträge.
    3. Falls < limit: füge neuen Eintrag hinzu und gib True zurück.
    4. Sonst: gib False zurück.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, bucket_key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        full_key = f"rl:{bucket_key}"
        member = f"{now}:{uuid.uuid4().hex}"

        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.zremrangebyscore(full_key, 0, cutoff)
            await pipe.zcard(full_key)
            await pipe.zadd(full_key, {member: now})
            await pipe.expire(full_key, window_seconds + 60)
            _, count, _, _ = await pipe.execute()

        if count >= limit:
            # Eintrag wurde fälschlich hinzugefügt — wieder entfernen.
            await self._redis.zrem(full_key, member)
            return False
        return True


class InMemoryRateLimiter:
    """Test-Implementierung ohne Redis."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}

    async def hit(self, bucket_key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        bucket = [t for t in self._buckets.get(bucket_key, []) if t > cutoff]
        if len(bucket) >= limit:
            self._buckets[bucket_key] = bucket
            return False
        bucket.append(now)
        self._buckets[bucket_key] = bucket
        return True
