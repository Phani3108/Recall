"""Skills routes — CRUD for reusable AI workflows."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Skill
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import SkillCreate, SkillResponse

router = APIRouter()


def _skill_to_response(s: Skill) -> SkillResponse:
    return SkillResponse(
        id=s.id,
        name=s.name,
        description=s.description,
        version=s.version,
        is_builtin=s.is_builtin,
        is_published=s.is_published,
        execution_count=s.execution_count,
        upvotes=s.upvotes,
        downvotes=s.downvotes,
        created_at=s.created_at,
    )


@router.get("/", response_model=list[SkillResponse])
async def list_skills(
    published_only: bool = Query(False),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[SkillResponse]:
    query = select(Skill).where(Skill.org_id == ctx.org_id)
    if published_only:
        query = query.where(Skill.is_published == True)
    query = query.order_by(Skill.execution_count.desc()).limit(50)
    result = await db.execute(query)
    return [_skill_to_response(s) for s in result.scalars().all()]


@router.post("/", response_model=SkillResponse, status_code=201)
async def create_skill(
    req: SkillCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    skill = Skill(
        org_id=ctx.org_id,
        name=req.name,
        description=req.description,
        steps=req.steps,
        trigger=req.trigger,
        created_by=ctx.user_id,
    )
    db.add(skill)
    await db.flush()
    return _skill_to_response(skill)


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.org_id == ctx.org_id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skill_to_response(skill)


@router.post("/{skill_id}/vote")
async def vote_skill(
    skill_id: uuid.UUID,
    direction: str = Query(..., pattern="^(up|down)$"),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.org_id == ctx.org_id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if direction == "up":
        skill.upvotes += 1
    else:
        skill.downvotes += 1
    await db.flush()

    return {"upvotes": skill.upvotes, "downvotes": skill.downvotes}


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.org_id == ctx.org_id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await db.delete(skill)
