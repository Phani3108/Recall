"""Lightweight Prometheus-style metrics collection.

Collects request counts, latency histograms, error rates, and active connections.
Exposes /metrics endpoint data as a dict (can be wired to a real Prometheus
exporter or returned as JSON from the governance dashboard).
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class _Histogram:
    """Simple histogram with configurable buckets."""
    buckets: tuple[float, ...] = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    _counts: dict[float, int] = field(default_factory=lambda: defaultdict(int))
    _sum: float = 0.0
    _total: int = 0
    _lock: Lock = field(default_factory=Lock)

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._total += 1
            for b in self.buckets:
                if value <= b:
                    self._counts[b] += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "count": self._total,
                "sum": round(self._sum, 4),
                "buckets": {str(b): self._counts.get(b, 0) for b in self.buckets},
            }


class MetricsCollector:
    """Application metrics singleton."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_count: dict[str, int] = defaultdict(int)
        self._error_count: dict[str, int] = defaultdict(int)
        self._status_codes: dict[int, int] = defaultdict(int)
        self._active_connections = 0
        self._latency = _Histogram()
        self._start_time = time.time()
        self._ai_tokens_used = 0
        self._ai_requests = 0

    # ── Request tracking ──────────────────────────────────────────

    def record_request(self, method: str, path: str, status_code: int, duration: float) -> None:
        key = f"{method} {path}"
        with self._lock:
            self._request_count[key] += 1
            self._status_codes[status_code] += 1
            if status_code >= 400:
                self._error_count[key] += 1
        self._latency.observe(duration)

    def inc_connections(self) -> None:
        with self._lock:
            self._active_connections += 1

    def dec_connections(self) -> None:
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    # ── AI-specific ───────────────────────────────────────────────

    def record_ai_usage(self, tokens: int) -> None:
        with self._lock:
            self._ai_tokens_used += tokens
            self._ai_requests += 1

    # ── Snapshot ──────────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            total_requests = sum(self._request_count.values())
            total_errors = sum(self._error_count.values())
            return {
                "uptime_seconds": round(time.time() - self._start_time, 1),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": round(total_errors / max(total_requests, 1), 4),
                "active_connections": self._active_connections,
                "status_codes": dict(self._status_codes),
                "top_endpoints": dict(
                    sorted(self._request_count.items(), key=lambda x: x[1], reverse=True)[:10]
                ),
                "top_errors": dict(
                    sorted(self._error_count.items(), key=lambda x: x[1], reverse=True)[:10]
                ),
                "latency": self._latency.snapshot(),
                "ai": {
                    "total_tokens": self._ai_tokens_used,
                    "total_requests": self._ai_requests,
                },
            }


# Global singleton
metrics = MetricsCollector()
