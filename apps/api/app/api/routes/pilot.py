"""Pilot routes — AI delegation proposals: propose, review, approve/reject, execute."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.api.schemas import (
    DelegationCreate,
    DelegationResponse,
    DelegationSuggestRequest,
    DelegationSuggestResponse,
)
from app.db.models import AuditAction, AuditLog, Delegation, DelegationStatus
from app.db.session import get_db
from app.services.delegation_payload import suggest_execution_payload
from app.services.execution_engine import execute_delegation

logger = logging.getLogger(__name__)

router = APIRouter()


def _delegation_to_response(d: Delegation) -> DelegationResponse:
    return DelegationResponse(
        id=d.id,
        action=d.action,
        reason=d.reason,
        tool=d.tool,
        confidence=d.confidence,
        status=d.status.value if isinstance(d.status, DelegationStatus) else d.status,
        proposed_for_user_id=d.proposed_for_user_id,
        resolved_by_user_id=d.resolved_by_user_id,
        resolved_at=d.resolved_at,
        execution_result=d.execution_result,
        execution_payload=d.execution_payload if isinstance(d.execution_payload, dict) else None,
        created_at=d.created_at,
    )


@router.get("/delegations", response_model=list[DelegationResponse])
async def list_delegations(
    status: str | None = Query(None),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[DelegationResponse]:
    query = select(Delegation).where(
        Delegation.org_id == ctx.org_id,
        Delegation.proposed_for_user_id == ctx.user_id,
    )

    if status:
        query = query.where(Delegation.status == DelegationStatus(status))

    query = query.order_by(Delegation.created_at.desc()).limit(50)
    result = await db.execute(query)
    return [_delegation_to_response(d) for d in result.scalars().all()]


@router.post("/delegations", response_model=DelegationResponse, status_code=201)
async def create_delegation(
    req: DelegationCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> DelegationResponse:
    ep = req.execution_payload if isinstance(req.execution_payload, dict) else None
    delegation = Delegation(
        org_id=ctx.org_id,
        action=req.action,
        reason=req.reason,
        tool=req.tool,
        confidence=req.confidence,
        status=DelegationStatus.PENDING,
        proposed_for_user_id=req.proposed_for_user_id or ctx.user_id,
        execution_payload=ep,
    )
    db.add(delegation)
    await db.flush()

    # Audit log
    db.add(AuditLog(
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        action=AuditAction.DELEGATION_PROPOSED,
        resource_type="delegation",
        resource_id=delegation.id,
        detail={"action": req.action, "tool": req.tool, "confidence": req.confidence},
    ))

    return _delegation_to_response(delegation)


@router.post("/delegations/suggest", response_model=DelegationSuggestResponse)
async def suggest_delegation_payload(
    req: DelegationSuggestRequest,
    _: OrgContext = Depends(get_org_context),
) -> DelegationSuggestResponse:
    """Suggest a structured ``execution_payload`` from natural language (regex, then LLM)."""
    payload, source = await suggest_execution_payload(req.action, req.tool)
    return DelegationSuggestResponse(execution_payload=payload, source=source)


@router.post("/delegations/{delegation_id}/approve", response_model=DelegationResponse)
async def approve_delegation(
    delegation_id: uuid.UUID,
    auto_execute: bool = Query(default=True, description="Execute immediately after approval"),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> DelegationResponse:
    result = await db.execute(
        select(Delegation).where(
            Delegation.id == delegation_id,
            Delegation.org_id == ctx.org_id,
        )
    )
    delegation = result.scalar_one_or_none()
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    if delegation.status != DelegationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Delegation already resolved")

    delegation.status = DelegationStatus.APPROVED
    delegation.resolved_by_user_id = ctx.user_id
    delegation.resolved_at = datetime.now(UTC)
    await db.flush()

    db.add(AuditLog(
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        action=AuditAction.DELEGATION_APPROVED,
        resource_type="delegation",
        resource_id=delegation.id,
        detail={"action": delegation.action, "tool": delegation.tool},
    ))

    # Auto-execute if requested
    if auto_execute:
        try:
            await execute_delegation(delegation, db)
            # execution_engine updates delegation status and records result
        except Exception as e:
            logger.warning("Auto-execution failed for delegation %s: %s", delegation_id, e)
            # Delegation stays in APPROVED state — user can retry via /execute

    return _delegation_to_response(delegation)


@router.post("/delegations/{delegation_id}/reject", response_model=DelegationResponse)
async def reject_delegation(
    delegation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> DelegationResponse:
    result = await db.execute(
        select(Delegation).where(
            Delegation.id == delegation_id,
            Delegation.org_id == ctx.org_id,
        )
    )
    delegation = result.scalar_one_or_none()
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    if delegation.status != DelegationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Delegation already resolved")

    delegation.status = DelegationStatus.REJECTED
    delegation.resolved_by_user_id = ctx.user_id
    delegation.resolved_at = datetime.now(UTC)
    await db.flush()

    db.add(AuditLog(
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        action=AuditAction.DELEGATION_REJECTED,
        resource_type="delegation",
        resource_id=delegation.id,
        detail={"action": delegation.action, "tool": delegation.tool},
    ))

    return _delegation_to_response(delegation)


@router.post("/delegations/{delegation_id}/undo", response_model=DelegationResponse)
async def undo_delegation(
    delegation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> DelegationResponse:
    result = await db.execute(
        select(Delegation).where(
            Delegation.id == delegation_id,
            Delegation.org_id == ctx.org_id,
        )
    )
    delegation = result.scalar_one_or_none()
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    if delegation.status == DelegationStatus.EXECUTED:
        raise HTTPException(status_code=400, detail="Cannot undo an executed delegation")

    delegation.status = DelegationStatus.PENDING
    delegation.resolved_by_user_id = None
    delegation.resolved_at = None
    await db.flush()

    return _delegation_to_response(delegation)


@router.get("/delegations/stats/summary")
async def delegation_stats(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Delegation.status, func.count(Delegation.id))
        .where(
            Delegation.org_id == ctx.org_id,
            Delegation.proposed_for_user_id == ctx.user_id,
        )
        .group_by(Delegation.status)
    )
    counts = {
        row[0].value if isinstance(row[0], DelegationStatus) else row[0]: row[1]
        for row in result.all()
    }
    total = sum(counts.values())
    approved = counts.get("approved", 0)
    return {
        "pending": counts.get("pending", 0),
        "approved": approved,
        "rejected": counts.get("rejected", 0),
        "executed": counts.get("executed", 0),
        "total": total,
        "approval_rate": round(approved / total * 100) if total > 0 else 0,
    }


@router.post("/delegations/{delegation_id}/execute")
async def execute_delegation_endpoint(
    delegation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Explicitly execute an approved delegation.

    Use this to retry execution of previously approved delegations
    that weren't auto-executed or whose execution failed.
    """
    result = await db.execute(
        select(Delegation).where(
            Delegation.id == delegation_id,
            Delegation.org_id == ctx.org_id,
        )
    )
    delegation = result.scalar_one_or_none()
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    if delegation.status == DelegationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Delegation must be approved before execution")
    if delegation.status == DelegationStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Cannot execute a rejected delegation")

    exec_result = await execute_delegation(delegation, db)

    return {
        "success": exec_result.success,
        "action": exec_result.action,
        "message": exec_result.message,
        "url": exec_result.url,
        "data": exec_result.data,
    }
