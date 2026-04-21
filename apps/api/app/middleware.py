"""Governance middleware — request audit logging, token budget enforcement,
rate limiting, security headers, and metrics collection.
"""

import logging
import time

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.db.models import TokenBudget
from app.db.session import async_session_factory
from app.services.metrics_service import metrics
from app.services.rate_limiter import ai_limiter, api_limiter, auth_limiter

logger = logging.getLogger(__name__)

# Paths that trigger token budget checks (AI-consuming endpoints)
AI_PATHS = {
    "/api/v1/agents/conversations/",
    "/api/v1/pilot/",
    "/api/v1/context/search",
    "/api/v1/flow/",
}
AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}
SKIP_AUDIT_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc", "/metrics"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # Modern browsers — CSP preferred
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client sliding-window rate limiter.

    Applies different limits: auth (10/min), AI (20/min), general API (120/min).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in SKIP_AUDIT_PATHS):
            return await call_next(request)

        # Identify client by IP (or forwarded header in production)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        # Pick the appropriate limiter
        if any(path.startswith(p) for p in AUTH_PATHS):
            limiter = auth_limiter
        elif any(path.startswith(p) for p in AI_PATHS):
            limiter = ai_limiter
        else:
            limiter = api_limiter

        allowed, headers = await limiter.allow(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
                headers=headers,
            )

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request metrics (count, latency, status codes)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in SKIP_AUDIT_PATHS):
            return await call_next(request)

        metrics.inc_connections()
        start = time.monotonic()
        try:
            response = await call_next(request)
            duration = time.monotonic() - start
            metrics.record_request(request.method, path, response.status_code, duration)

            # Log slow requests
            if duration > 5.0:
                logger.warning(
                    "Slow request: %s %s took %.1fs", request.method, path, duration
                )

            return response
        finally:
            metrics.dec_connections()


class GovernanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in SKIP_AUDIT_PATHS):
            return await call_next(request)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        if duration_ms > 5000:
            logger.warning("Slow request: %s %s took %dms", request.method, path, duration_ms)

        return response


class TokenBudgetMiddleware(BaseHTTPMiddleware):
    """Check token budget before AI operations.

    Returns 429 if the org has exceeded its monthly token budget.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if request.method != "POST" or not any(path.startswith(p) for p in AI_PATHS):
            return await call_next(request)

        org_id = request.state.__dict__.get("org_id") if hasattr(request, "state") else None

        if org_id:
            try:
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(TokenBudget).where(
                            TokenBudget.org_id == org_id,
                            TokenBudget.scope == "org",
                        )
                    )
                    budget = result.scalar_one_or_none()

                    if budget and budget.tokens_used >= budget.monthly_limit:
                        return JSONResponse(
                            status_code=429,
                            content={
                                "detail": "Monthly token budget exceeded",
                                "budget_limit": budget.monthly_limit,
                                "tokens_used": budget.tokens_used,
                            },
                        )
            except Exception:
                logger.warning("Token budget check failed", exc_info=True)

        return await call_next(request)
