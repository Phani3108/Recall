"""Analytics engine — time-series aggregation for tokens, costs, productivity.

Provides weekly/monthly breakdowns and trend data for the executive dashboard.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentProposal,
    AuditLog,
    ContextEntity,
    Conversation,
    Delegation,
    DelegationStatus,
    Integration,
    Message,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)


async def get_token_trends(
    org_id: uuid.UUID,
    db: AsyncSession,
    days: int = 30,
) -> list[dict]:
    """Daily token usage for the last N days."""
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(AuditLog.created_at).label("day"),
            func.sum(AuditLog.tokens_consumed).label("tokens"),
            func.sum(AuditLog.cost_usd).label("cost"),
            func.count().label("requests"),
        )
        .where(AuditLog.org_id == org_id, AuditLog.created_at >= since)
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at))
    )
    return [
        {"day": str(row.day), "tokens": int(row.tokens or 0), "cost": float(row.cost or 0), "requests": row.requests}
        for row in result.all()
    ]


async def get_productivity_stats(
    org_id: uuid.UUID,
    db: AsyncSession,
    days: int = 30,
) -> dict:
    """Productivity breakdown: tasks completed, PRs merged, delegation success rate."""
    since = datetime.now(UTC) - timedelta(days=days)

    # Task stats
    tasks_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0)).label("completed"),
        )
        .where(Task.org_id == org_id, Task.created_at >= since)
    )
    task_row = tasks_result.one()

    # Delegation stats
    del_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((Delegation.status == DelegationStatus.EXECUTED, 1), else_=0)).label("executed"),
            func.sum(case((Delegation.status == DelegationStatus.APPROVED, 1), else_=0)).label("approved"),
        )
        .where(Delegation.org_id == org_id, Delegation.created_at >= since)
    )
    del_row = del_result.one()

    # Conversations
    conv_result = await db.execute(
        select(func.count()).where(Conversation.org_id == org_id, Conversation.created_at >= since)
    )
    conversations = conv_result.scalar() or 0

    # Messages
    msg_result = await db.execute(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.org_id == org_id, Message.created_at >= since)
    )
    messages = msg_result.scalar() or 0

    return {
        "period_days": days,
        "tasks_created": int(task_row.total or 0),
        "tasks_completed": int(task_row.completed or 0),
        "task_completion_rate": round(int(task_row.completed or 0) / max(int(task_row.total or 0), 1), 2),
        "delegations_total": int(del_row.total or 0),
        "delegations_executed": int(del_row.executed or 0),
        "delegations_approved": int(del_row.approved or 0),
        "conversations": conversations,
        "messages": messages,
    }


async def get_top_ai_users(
    org_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """Top users by AI token consumption."""
    from app.db.models import User
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.sum(AuditLog.tokens_consumed).label("tokens"),
            func.sum(AuditLog.cost_usd).label("cost"),
            func.count().label("requests"),
        )
        .where(
            AuditLog.org_id == org_id,
            AuditLog.user_id.isnot(None),
            AuditLog.tokens_consumed > 0,
        )
        .group_by(AuditLog.user_id)
        .order_by(func.sum(AuditLog.tokens_consumed).desc())
        .limit(limit)
    )
    rows = result.all()

    users = []
    for row in rows:
        user_result = await db.execute(select(User).where(User.id == row.user_id))
        user = user_result.scalar_one_or_none()
        users.append({
            "user_id": str(row.user_id),
            "name": user.name if user else "Unknown",
            "email": user.email if user else "",
            "tokens": int(row.tokens or 0),
            "cost": round(float(row.cost or 0), 4),
            "requests": row.requests,
        })
    return users


async def get_integration_health(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    """Per-integration health: sync status, entity count, last sync time."""
    result = await db.execute(
        select(Integration).where(Integration.org_id == org_id)
    )
    integrations = result.scalars().all()

    health = []
    for intg in integrations:
        entity_count_result = await db.execute(
            select(func.count()).where(
                ContextEntity.org_id == org_id,
                ContextEntity.source_integration_id == intg.id,
            )
        )
        entity_count = entity_count_result.scalar() or 0

        health.append({
            "id": str(intg.id),
            "provider": intg.provider.value if hasattr(intg.provider, "value") else str(intg.provider),
            "status": intg.status.value if hasattr(intg.status, "value") else str(intg.status),
            "entity_count": entity_count,
            "last_synced_at": intg.last_synced_at.isoformat() if intg.last_synced_at else None,
            "synced_entity_count": intg.synced_entity_count,
        })
    return health


async def get_agent_intelligence(
    org_id: uuid.UUID,
    db: AsyncSession,
    days: int = 7,
) -> dict:
    """Agent intelligence report: proposals, approvals, pattern trends."""
    since = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(
            AgentProposal.pattern_type,
            AgentProposal.status,
            func.count().label("count"),
        )
        .where(AgentProposal.org_id == org_id, AgentProposal.created_at >= since)
        .group_by(AgentProposal.pattern_type, AgentProposal.status)
    )

    patterns: dict[str, dict] = {}
    for row in result.all():
        pt = row.pattern_type
        if pt not in patterns:
            patterns[pt] = {"total": 0, "approved": 0, "rejected": 0, "pending": 0}
        patterns[pt]["total"] += row.count
        patterns[pt][row.status] = patterns[pt].get(row.status, 0) + row.count

    total_proposals = sum(p["total"] for p in patterns.values())
    total_approved = sum(p.get("approved", 0) for p in patterns.values())

    return {
        "period_days": days,
        "total_proposals": total_proposals,
        "total_approved": total_approved,
        "approval_rate": round(total_approved / max(total_proposals, 1), 2),
        "patterns": patterns,
    }


async def get_cost_forecast(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Simple cost forecast based on the last 30 days of spending."""
    trends = await get_token_trends(org_id, db, days=30)
    if not trends:
        return {"daily_avg": 0, "projected_monthly": 0, "trend": "flat"}

    costs = [t["cost"] for t in trends]
    daily_avg = sum(costs) / len(costs)
    projected = daily_avg * 30

    # Trend: compare last 7 days vs previous 7 days
    if len(costs) >= 14:
        recent = sum(costs[-7:]) / 7
        previous = sum(costs[-14:-7]) / 7
        if recent > previous * 1.1:
            trend = "increasing"
        elif recent < previous * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {
        "daily_avg": round(daily_avg, 4),
        "projected_monthly": round(projected, 2),
        "trend": trend,
        "data_points": len(costs),
    }
