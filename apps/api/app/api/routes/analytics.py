"""Analytics routes — executive dashboard data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.db.session import get_db
from app.services.analytics_engine import (
    get_agent_intelligence,
    get_cost_forecast,
    get_integration_health,
    get_productivity_stats,
    get_token_trends,
    get_top_ai_users,
)

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=7, le=365),
) -> dict:
    ctx.require_role("owner", "admin")
    productivity = await get_productivity_stats(ctx.org_id, db, days)
    forecast = await get_cost_forecast(ctx.org_id, db)
    return {
        "productivity": productivity,
        "cost_forecast": forecast,
    }


@router.get("/token-trends")
async def token_trends(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=7, le=365),
) -> list[dict]:
    ctx.require_role("owner", "admin")
    return await get_token_trends(ctx.org_id, db, days)


@router.get("/top-users")
async def top_users(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    ctx.require_role("owner", "admin")
    return await get_top_ai_users(ctx.org_id, db, limit)


@router.get("/integration-health")
async def integration_health(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    ctx.require_role("owner", "admin")
    return await get_integration_health(ctx.org_id, db)


@router.get("/agent-intelligence")
async def agent_intelligence(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> dict:
    ctx.require_role("owner", "admin")
    return await get_agent_intelligence(ctx.org_id, db, days)


@router.get("/cost-forecast")
async def cost_forecast(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ctx.require_role("owner", "admin")
    return await get_cost_forecast(ctx.org_id, db)
