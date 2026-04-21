"""Notification service — in-app notification management.

Creates, retrieves, marks-read, and dismisses notifications for users.
Notifications are created by system events (sync complete, proposal created,
delegation executed, etc.) and consumed by the frontend bell icon.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification

logger = logging.getLogger(__name__)


async def create_notification(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    kind: str,
    title: str,
    body: str,
    db: AsyncSession,
    link: str | None = None,
    icon: str | None = None,
    metadata: dict | None = None,
) -> Notification:
    """Create a new in-app notification for a user."""
    n = Notification(
        org_id=org_id,
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link=link,
        icon=icon,
        meta=metadata or {},
    )
    db.add(n)
    await db.flush()
    return n


async def get_notifications(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    """Retrieve notifications for a user, newest first."""
    q = (
        select(Notification)
        .where(Notification.org_id == org_id, Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    result = await db.execute(q)
    return list(result.scalars().all())


async def unread_count(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.org_id == org_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    return result.scalar() or 0


async def mark_read(
    notification_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
            Notification.user_id == user_id,
        )
        .values(read_at=datetime.now(UTC))
    )
    return result.rowcount > 0


async def mark_all_read(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.org_id == org_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    return result.rowcount


async def dismiss_notification(
    notification_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
            Notification.user_id == user_id,
        )
    )
    n = result.scalar_one_or_none()
    if n:
        await db.delete(n)
        return True
    return False
