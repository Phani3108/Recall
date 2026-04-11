"""Team routes — CRUD for teams within an org."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Team, TeamMember, User
from app.api.deps import get_org_context, OrgContext

router = APIRouter()


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = "member"


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    slug: str
    avatar_url: str | None
    member_count: int
    created_at: str


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    role: str
    joined_at: str


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[TeamResponse]:
    result = await db.execute(
        select(Team).where(Team.org_id == ctx.org_id).order_by(Team.name)
    )
    teams = result.scalars().all()
    responses = []
    for t in teams:
        count_result = await db.execute(
            select(func.count()).select_from(TeamMember).where(TeamMember.team_id == t.id)
        )
        responses.append(TeamResponse(
            id=t.id, name=t.name, description=t.description, slug=t.slug,
            avatar_url=t.avatar_url, member_count=count_result.scalar() or 0,
            created_at=t.created_at.isoformat(),
        ))
    return responses


@router.post("/", response_model=TeamResponse, status_code=201)
async def create_team(
    req: TeamCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    ctx.require_role("owner", "admin")
    team = Team(org_id=ctx.org_id, name=req.name, description=req.description, slug=req.slug)
    db.add(team)
    await db.flush()
    # Add creator as team lead
    db.add(TeamMember(org_id=ctx.org_id, team_id=team.id, user_id=ctx.user_id, role="lead"))
    await db.flush()
    return TeamResponse(
        id=team.id, name=team.name, description=team.description, slug=team.slug,
        avatar_url=team.avatar_url, member_count=1, created_at=team.created_at.isoformat(),
    )


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_team_members(
    team_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[TeamMemberResponse]:
    result = await db.execute(
        select(TeamMember, User)
        .join(User, TeamMember.user_id == User.id)
        .where(TeamMember.team_id == team_id, TeamMember.org_id == ctx.org_id)
    )
    return [
        TeamMemberResponse(
            id=tm.id, user_id=tm.user_id, user_name=u.name, user_email=u.email,
            role=tm.role, joined_at=tm.created_at.isoformat(),
        )
        for tm, u in result.all()
    ]


@router.post("/{team_id}/members", status_code=201)
async def add_team_member(
    team_id: uuid.UUID,
    req: TeamMemberAdd,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ctx.require_role("owner", "admin")
    db.add(TeamMember(org_id=ctx.org_id, team_id=team_id, user_id=req.user_id, role=req.role))
    await db.flush()
    return {"status": "added"}


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    ctx.require_role("owner", "admin")
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.org_id == ctx.org_id,
        )
    )
    member = result.scalar_one_or_none()
    if member:
        await db.delete(member)


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    ctx.require_role("owner", "admin")
    result = await db.execute(
        select(Team).where(Team.id == team_id, Team.org_id == ctx.org_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    await db.delete(team)
