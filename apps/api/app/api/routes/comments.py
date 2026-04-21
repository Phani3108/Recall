"""Comment routes — threaded comments on tasks, delegations, proposals."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.db.models import Comment, User
from app.db.session import get_db

router = APIRouter()

ALLOWED_RESOURCE_TYPES = {"task", "delegation", "proposal", "skill"}


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_id: uuid.UUID | None = None


class CommentResponse(BaseModel):
    id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    content: str
    parent_id: uuid.UUID | None
    created_at: str


@router.get("/{resource_type}/{resource_id}", response_model=list[CommentResponse])
async def list_comments(
    resource_type: str,
    resource_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[CommentResponse]:
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid resource type: {resource_type}")
    result = await db.execute(
        select(Comment, User)
        .join(User, Comment.user_id == User.id)
        .where(
            Comment.org_id == ctx.org_id,
            Comment.resource_type == resource_type,
            Comment.resource_id == resource_id,
        )
        .order_by(Comment.created_at.asc())
    )
    return [
        CommentResponse(
            id=c.id, resource_type=c.resource_type, resource_id=c.resource_id,
            user_id=c.user_id, user_name=u.name, content=c.content,
            parent_id=c.parent_id, created_at=c.created_at.isoformat(),
        )
        for c, u in result.all()
    ]


@router.post("/{resource_type}/{resource_id}", response_model=CommentResponse, status_code=201)
async def create_comment(
    resource_type: str,
    resource_id: uuid.UUID,
    req: CommentCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid resource type: {resource_type}")
    comment = Comment(
        org_id=ctx.org_id,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=ctx.user_id,
        content=req.content,
        parent_id=req.parent_id,
    )
    db.add(comment)
    await db.flush()

    user_result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = user_result.scalar_one()

    return CommentResponse(
        id=comment.id, resource_type=resource_type, resource_id=resource_id,
        user_id=ctx.user_id, user_name=user.name, content=comment.content,
        parent_id=comment.parent_id, created_at=comment.created_at.isoformat(),
    )


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.org_id == ctx.org_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != ctx.user_id:
        ctx.require_role("owner", "admin")
    await db.delete(comment)
