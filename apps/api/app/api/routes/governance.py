from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import AuditLog, TokenBudget, Integration, Conversation, Skill
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import AuditLogResponse, TokenBudgetResponse, GovernanceDashboard

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
