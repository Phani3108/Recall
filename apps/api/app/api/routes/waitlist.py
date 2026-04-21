"""Waitlist routes — collect early access signups (no auth required)."""

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.db.models import WaitlistEntry
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    company: str | None = None


class WaitlistResponse(BaseModel):
    status: str
    message: str
    position: int | None = None


@router.post("/join", response_model=WaitlistResponse, status_code=201)
async def join_waitlist(
    req: WaitlistRequest,
    db: AsyncSession = Depends(get_db),
) -> WaitlistResponse:
    # Check if already on the list
    result = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.email == req.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return WaitlistResponse(
            status="exists",
            message="You're already on the waitlist! We'll be in touch soon.",
        )

    # Get current count for position
    count_result = await db.execute(select(func.count()).select_from(WaitlistEntry))
    position = (count_result.scalar() or 0) + 1

    entry = WaitlistEntry(
        email=req.email,
        name=req.name,
        company=req.company,
    )
    db.add(entry)
    await db.flush()

    logger.info(f"Waitlist signup #{position}: {req.email}")

    return WaitlistResponse(
        status="joined",
        message="You're on the list! We'll reach out when early access opens.",
        position=position,
    )


@router.get("/entries")
async def list_waitlist_entries(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List all waitlist entries (admin only)."""
    ctx.require_role("owner", "admin")
    result = await db.execute(
        select(WaitlistEntry)
        .order_by(WaitlistEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = result.scalars().all()
    count_result = await db.execute(select(func.count()).select_from(WaitlistEntry))
    total = count_result.scalar() or 0
    return {
        "total": total,
        "entries": [
            {
                "id": str(e.id),
                "email": e.email,
                "name": e.name,
                "company": e.company,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ],
    }
