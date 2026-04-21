"""Admin routes — full visibility for org owners/admins."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.api.schemas import AdminActivityRow, AdminOverview, AdminUserRow
from app.db.models import (
    AuditLog,
    Conversation,
    Delegation,
    Integration,
    OrgMembership,
    Task,
    User,
)
from app.db.session import get_db

router = APIRouter()


@router.get("/overview", response_model=AdminOverview)
async def admin_overview(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> AdminOverview:
    ctx.require_role("owner", "admin")
    oid = ctx.org_id

    total_users = (await db.execute(
        select(func.count()).select_from(OrgMembership).where(OrgMembership.org_id == oid)
    )).scalar() or 0

    total_conversations = (await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.org_id == oid)
    )).scalar() or 0

    tokens_result = (await db.execute(
        select(func.coalesce(func.sum(AuditLog.tokens_consumed), 0)).where(AuditLog.org_id == oid)
    )).scalar() or 0

    cost_result = (await db.execute(
        select(func.coalesce(func.sum(AuditLog.cost_usd), 0.0)).where(AuditLog.org_id == oid)
    )).scalar() or 0.0

    total_integrations = (await db.execute(
        select(func.count()).select_from(Integration).where(Integration.org_id == oid)
    )).scalar() or 0

    total_tasks = (await db.execute(
        select(func.count()).select_from(Task).where(Task.org_id == oid)
    )).scalar() or 0

    total_delegations = (await db.execute(
        select(func.count()).select_from(Delegation).where(Delegation.org_id == oid)
    )).scalar() or 0

    return AdminOverview(
        total_users=total_users,
        total_orgs=1,
        total_conversations=total_conversations,
        total_tokens_used=tokens_result,
        total_cost_usd=cost_result,
        total_integrations=total_integrations,
        total_tasks=total_tasks,
        total_delegations=total_delegations,
    )


@router.get("/users", response_model=list[AdminUserRow])
async def admin_list_users(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserRow]:
    ctx.require_role("owner", "admin")
    result = await db.execute(
        select(User, OrgMembership)
        .join(OrgMembership, OrgMembership.user_id == User.id)
        .where(OrgMembership.org_id == ctx.org_id)
        .order_by(User.created_at.desc())
    )
    rows = result.all()
    return [
        AdminUserRow(
            id=user.id,
            email=user.email,
            name=user.name,
            role=membership.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        for user, membership in rows
    ]


@router.get("/activity", response_model=list[AdminActivityRow])
async def admin_activity(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AdminActivityRow]:
    ctx.require_role("owner", "admin")
    result = await db.execute(
        select(AuditLog, User)
        .outerjoin(User, AuditLog.user_id == User.id)
        .where(AuditLog.org_id == ctx.org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    return [
        AdminActivityRow(
            id=log.id,
            user_email=user.email if user else None,
            user_name=user.name if user else None,
            action=log.action.value if hasattr(log.action, 'value') else str(log.action),
            resource_type=log.resource_type,
            detail=log.detail,
            tokens_consumed=log.tokens_consumed,
            cost_usd=log.cost_usd,
            created_at=log.created_at,
        )
        for log, user in rows
    ]
