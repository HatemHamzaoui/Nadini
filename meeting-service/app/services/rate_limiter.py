"""Redis-basierter Sliding-Window Rate Limiter."""
from __future__ import annotations

import time
import uuid
from typing import Protocol

from redis.asyncio import Redis


class RateLimiter(Protocol):
    async def hit(self, bucket_key: str, limit: int, window_seconds: int) -> bool: ...


class RedisRateLimiter:
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
            await self._redis.zrem(full_key, member)
            return False
        return True
