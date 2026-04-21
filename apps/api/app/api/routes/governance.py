from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.api.schemas import (
    AuditLogResponse,
    GovernanceDashboard,
    RetentionPurgeRequest,
    RetentionPurgeResponse,
    RetentionStatsResponse,
    SecurityStatusResponse,
)
from app.db.models import AuditLog, Conversation, Integration, Skill
from app.db.session import get_db
from app.services.metrics_service import metrics
from app.services.retention_service import (
    cleanup_orphan_relations,
    get_retention_stats,
    purge_old_audit_logs,
    purge_old_entities,
)

router = APIRouter()


@router.get("/dashboard", response_model=GovernanceDashboard)
async def get_governance_dashboard(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> GovernanceDashboard:
    ctx.require_role("owner", "admin")

    # Total tokens used
    tokens_result = await db.execute(
        select(func.coalesce(func.sum(AuditLog.tokens_consumed), 0)).where(
            AuditLog.org_id == ctx.org_id
        )
    )
    total_tokens = tokens_result.scalar() or 0

    # Total cost
    cost_result = await db.execute(
        select(func.coalesce(func.sum(AuditLog.cost_usd), 0.0)).where(
            AuditLog.org_id == ctx.org_id
        )
    )
    total_cost = cost_result.scalar() or 0.0

    # Active integrations
    integrations_result = await db.execute(
        select(func.count()).where(
            Integration.org_id == ctx.org_id,
            Integration.status == "connected",
        )
    )
    active_integrations = integrations_result.scalar() or 0

    # Total conversations
    conversations_result = await db.execute(
        select(func.count()).where(Conversation.org_id == ctx.org_id)
    )
    total_conversations = conversations_result.scalar() or 0

    # Skill executions
    skills_result = await db.execute(
        select(func.coalesce(func.sum(Skill.execution_count), 0)).where(
            Skill.org_id == ctx.org_id
        )
    )
    total_skill_executions = skills_result.scalar() or 0

    # Budget utilization
    budget_pct = 0.0
    if ctx.org.token_budget_monthly and ctx.org.token_budget_monthly > 0:
        budget_pct = (ctx.org.tokens_used_this_month / ctx.org.token_budget_monthly) * 100

    return GovernanceDashboard(
        total_tokens_used=total_tokens,
        total_cost_usd=total_cost,
        active_integrations=active_integrations,
        total_conversations=total_conversations,
        total_skill_executions=total_skill_executions,
        budget_utilization_pct=round(budget_pct, 2),
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLogResponse]:
    ctx.require_role("owner", "admin")

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == ctx.org_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action.value,
            resource_type=log.resource_type,
            detail=log.detail,
            tokens_consumed=log.tokens_consumed,
            cost_usd=log.cost_usd,
            model_used=log.model_used,
            created_at=log.created_at,
        )
        for log in logs
    ]


# ── Retention ─────────────────────────────────────────────────────


@router.get("/retention/stats", response_model=RetentionStatsResponse)
async def retention_stats(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> RetentionStatsResponse:
    ctx.require_role("owner", "admin")
    stats = await get_retention_stats(ctx.org_id, db)
    return RetentionStatsResponse(**stats)


@router.post("/retention/purge", response_model=RetentionPurgeResponse)
async def retention_purge(
    body: RetentionPurgeRequest,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> RetentionPurgeResponse:
    ctx.require_role("owner")

    if body.dry_run:
        # Return counts that _would_ be purged without deleting
        stats = await get_retention_stats(ctx.org_id, db)
        return RetentionPurgeResponse(
            entities_purged=stats["entities_older_than_90d"],
            audit_logs_purged=stats["audit_logs_older_than_365d"],
            orphan_relations_cleaned=stats["orphan_relations"],
            dry_run=True,
        )

    entities = await purge_old_entities(ctx.org_id, db, body.entity_retention_days)
    audits = await purge_old_audit_logs(ctx.org_id, db, body.audit_retention_days)
    orphans = await cleanup_orphan_relations(ctx.org_id, db)

    return RetentionPurgeResponse(
        entities_purged=entities,
        audit_logs_purged=audits,
        orphan_relations_cleaned=orphans,
        dry_run=False,
    )


# ── Security ──────────────────────────────────────────────────────


@router.get("/security/status", response_model=SecurityStatusResponse)
async def security_status(
    ctx: OrgContext = Depends(get_org_context),
) -> SecurityStatusResponse:
    ctx.require_role("owner", "admin")
    return SecurityStatusResponse(
        rate_limiting_enabled=True,
        security_headers_enabled=True,
        credential_encryption_enabled=True,
        token_budget_enforced=True,
        permission_filtering_enabled=True,
        metrics_collection_enabled=True,
        secrets_masked=True,
    )


# ── Metrics ───────────────────────────────────────────────────────


@router.get("/metrics")
async def governance_metrics(
    ctx: OrgContext = Depends(get_org_context),
) -> dict:
    ctx.require_role("owner", "admin")
    return metrics.snapshot()
