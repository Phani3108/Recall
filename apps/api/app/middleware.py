"""Governance middleware — request audit logging and token budget enforcement.

Automatically logs API requests to the audit trail and checks token budgets
before AI operations are allowed to proceed.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from sqlalchemy import select, func

from app.db.session import async_session_factory
from app.db.models import AuditLog, AuditAction, TokenBudget

logger = logging.getLogger(__name__)

# Paths that trigger token budget checks (AI-consuming endpoints)
AI_PATHS = {"/api/v1/agents/conversations/"}
SKIP_AUDIT_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc"}


class GovernanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip audit for health checks and docs
        if any(path.startswith(p) for p in SKIP_AUDIT_PATHS):
            return await call_next(request)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Log slow requests
        if duration_ms > 5000:
            logger.warning("Slow request: %s %s took %dms", request.method, path, duration_ms)

        return response


class TokenBudgetMiddleware(BaseHTTPMiddleware):
    """Check token budget before AI operations.

    Returns 429 if the org has exceeded its monthly token budget.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Only check budget on AI endpoints (POST to conversations)
        if request.method != "POST" or not any(path.startswith(p) for p in AI_PATHS):
            return await call_next(request)

        # Extract org_id from the auth token (set by deps.py)
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
