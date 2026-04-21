"""Notification routes — in-app notification bell."""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.db.session import get_db
from app.services.notification_service import (
    dismiss_notification,
    get_notifications,
    mark_all_read,
    mark_read,
    unread_count,
)

router = APIRouter()


class NotificationResponse(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    link: str | None
    icon: str | None
    read_at: str | None
    created_at: str


class NotificationSummary(BaseModel):
    unread_count: int
    notifications: list[NotificationResponse]


@router.get("/", response_model=NotificationSummary)
async def list_notifications(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    unread_only: bool = Query(False),
    limit: int = Query(default=30, ge=1, le=100),
) -> NotificationSummary:
    notifs = await get_notifications(ctx.org_id, ctx.user_id, db, unread_only=unread_only, limit=limit)
    count = await unread_count(ctx.org_id, ctx.user_id, db)
    return NotificationSummary(
        unread_count=count,
        notifications=[
            NotificationResponse(
                id=n.id,
                kind=n.kind,
                title=n.title,
                body=n.body,
                link=n.link,
                icon=n.icon,
                read_at=n.read_at.isoformat() if n.read_at else None,
                created_at=n.created_at.isoformat(),
            )
            for n in notifs
        ],
    )


@router.get("/unread-count")
async def get_unread_count(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await unread_count(ctx.org_id, ctx.user_id, db)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ok = await mark_read(notification_id, ctx.org_id, ctx.user_id, db)
    return {"ok": ok}


@router.post("/read-all")
async def read_all_notifications(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await mark_all_read(ctx.org_id, ctx.user_id, db)
    return {"marked_read": count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ok = await dismiss_notification(notification_id, ctx.org_id, ctx.user_id, db)
    return {"ok": ok}
