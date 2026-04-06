from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Organization, OrgMembership, User
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import OrgResponse, OrgMemberResponse

router = APIRouter()


@router.get("/current", response_model=OrgResponse)
async def get_current_org(ctx: OrgContext = Depends(get_org_context)) -> OrgResponse:
    org = ctx.org
    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        token_budget_monthly=org.token_budget_monthly,
        tokens_used_this_month=org.tokens_used_this_month,
        created_at=org.created_at,
    )


@router.get("/members", response_model=list[OrgMemberResponse])
async def list_members(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[OrgMemberResponse]:
    result = await db.execute(
        select(OrgMembership, User)
        .join(User, OrgMembership.user_id == User.id)
        .where(OrgMembership.org_id == ctx.org_id)
    )
    rows = result.all()
    return [
        OrgMemberResponse(
            id=membership.id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=membership.role.value,
            joined_at=membership.created_at,
        )
        for membership, user in rows
    ]
