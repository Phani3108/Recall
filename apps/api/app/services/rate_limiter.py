"""Rate limiting — token-bucket (in-memory) or fixed-window (Redis) per client key.

Redis is used when ``settings.use_redis_rate_limiter`` is true and the server can
ping Redis at startup; otherwise falls back to in-memory (single-replica only).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiterBackend(ABC):
    """Async rate limiter — ``allow`` returns (allowed, response_headers)."""

    @abstractmethod
    async def allow(self, key: str) -> tuple[bool, dict]:
        raise NotImplementedError


class MemoryRateLimiter(RateLimiterBackend):
    """Token-bucket limiter in process memory."""

    def __init__(self, rate: int = 60, window: float = 60.0):
        self.rate = rate
        self.window = window
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=float(rate), last_refill=time.monotonic())
        )

    async def allow(self, key: str) -> tuple[bool, dict]:
        now = time.monotonic()
        bucket = self._buckets[key]

        elapsed = now - bucket.last_refill
        bucket.tokens = min(
            float(self.rate), bucket.tokens + elapsed * (self.rate / self.window)
        )
        bucket.last_refill = now

        headers = {
            "X-RateLimit-Limit": str(self.rate),
            "X-RateLimit-Remaining": str(max(0, int(bucket.tokens) - 1)),
            "X-RateLimit-Reset": str(int(now + self.window)),
        }

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, headers

        headers["Retry-After"] = str(int(self.window - elapsed) + 1)
        return False, headers

    def cleanup(self, max_age: float = 300.0) -> int:
        now = time.monotonic()
        stale = [k for k, v in self._buckets.items() if now - v.last_refill > max_age]
        for k in stale:
            del self._buckets[k]
        return len(stale)


class RedisFixedWindowLimiter(RateLimiterBackend):
    """Fixed-window counter in Redis (works across API replicas)."""

    def __init__(self, redis_client: Redis, key_prefix: str, rate: int, window_sec: float):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.rate = rate
        self.window_sec = max(1, int(window_sec))

    async def allow(self, key: str) -> tuple[bool, dict]:
        now = int(time.time())
        bucket = now // self.window_sec
        rk = f"{self.key_prefix}:{key}:{bucket}"
        n = await self.redis.incr(rk)
        if n == 1:
            await self.redis.expire(rk, self.window_sec + 5)

        allowed = n <= self.rate
        remaining = max(0, self.rate - n) if allowed else 0
        reset_ts = (bucket + 1) * self.window_sec
        headers = {
            "X-RateLimit-Limit": str(self.rate),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_ts),
        }
        if not allowed:
            headers["Retry-After"] = str(self.window_sec)
        return allowed, headers


# ── Active backends (set by init_limiters at startup) ──

api_limiter: RateLimiterBackend = MemoryRateLimiter(rate=120, window=60.0)
ai_limiter: RateLimiterBackend = MemoryRateLimiter(rate=20, window=60.0)
auth_limiter: RateLimiterBackend = MemoryRateLimiter(rate=10, window=60.0)

_redis_client: Redis | None = None


def _memory_defaults() -> tuple[MemoryRateLimiter, MemoryRateLimiter, MemoryRateLimiter]:
    return (
        MemoryRateLimiter(rate=120, window=60.0),
        MemoryRateLimiter(rate=20, window=60.0),
        MemoryRateLimiter(rate=10, window=60.0),
    )


async def init_limiters() -> None:
    """Select Redis or in-memory rate limiters. Call from application lifespan."""
    global api_limiter, ai_limiter, auth_limiter, _redis_client

    from app.config import settings

    api_limiter, ai_limiter, auth_limiter = _memory_defaults()

    if not settings.use_redis_rate_limiter:
        logger.info("Rate limiting: in-memory backend (test mode or redis_rate_limiting disabled)")
        return

    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        _redis_client = client
        api_limiter = RedisFixedWindowLimiter(client, "rl:api", 120, 60.0)
        ai_limiter = RedisFixedWindowLimiter(client, "rl:ai", 20, 60.0)
        auth_limiter = RedisFixedWindowLimiter(client, "rl:auth", 10, 60.0)
        logger.info("Rate limiting: Redis fixed-window backend")
    except Exception as e:
        logger.warning("Redis unavailable for rate limiting (%s); using in-memory", e)


async def shutdown_limiters() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
