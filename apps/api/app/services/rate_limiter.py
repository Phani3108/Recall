"""Rate limiting — sliding-window rate limiter backed by in-memory store.

Uses a simple token-bucket algorithm per (client_ip, org_id) pair.
In production with multiple replicas, swap to Redis-backed implementation.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Sliding-window token-bucket rate limiter.

    Args:
        rate: Number of requests allowed per window.
        window: Window size in seconds.
    """

    def __init__(self, rate: int = 60, window: float = 60.0):
        self.rate = rate
        self.window = window
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=float(rate), last_refill=time.monotonic())
        )

    def allow(self, key: str) -> tuple[bool, dict]:
        """Check if a request is allowed for the given key.

        Returns (allowed, headers) where headers contains rate limit info.
        """
        now = time.monotonic()
        bucket = self._buckets[key]

        # Refill tokens based on elapsed time
        elapsed = now - bucket.last_refill
        bucket.tokens = min(float(self.rate), bucket.tokens + elapsed * (self.rate / self.window))
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
        """Remove stale buckets older than max_age seconds. Returns count removed."""
        now = time.monotonic()
        stale = [k for k, v in self._buckets.items() if now - v.last_refill > max_age]
        for k in stale:
            del self._buckets[k]
        return len(stale)


# ── Pre-configured limiters ──

# General API: 120 req/min per client
api_limiter = RateLimiter(rate=120, window=60.0)

# AI endpoints (conversations, chat): 20 req/min per client
ai_limiter = RateLimiter(rate=20, window=60.0)

# Auth endpoints (login, register): 10 req/min per client
auth_limiter = RateLimiter(rate=10, window=60.0)
