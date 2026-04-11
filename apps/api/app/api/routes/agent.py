"""Agent routes — autonomous agent proposals, feedback, config, and manual triggers."""

import logging
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import AgentProposal, AgentConfig
from app.api.deps import get_org_context, OrgContext
from app.agents.observer import observe
from app.agents.planner import plan
from app.agents.learner import record_feedback, get_learning_summary

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response schemas ──

class ProposalResponse(BaseModel):
    id: uuid.UUID
    pattern_type: str
    title: str
    description: str
    suggested_action: str
    tool: str
    confidence: float
    priority: str
    status: str
    entity_ids: list[str]
    context_snapshot: dict
    delegation_id: uuid.UUID | None
    created_at: datetime


class AgentConfigResponse(BaseModel):
    enabled: bool
    mode: str
    confidence_threshold: float
    auto_approve_threshold: float
    patterns_enabled: list[str]


class AgentConfigUpdate(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    confidence_threshold: float | None = None
    auto_approve_threshold: float | None = None
    patterns_enabled: list[str] | None = None


# ── Proposals ──

def _proposal_to_response(p: AgentProposal) -> ProposalResponse:
    return ProposalResponse(
        id=p.id,
        pattern_type=p.pattern_type,
        title=p.title,
        description=p.description,
        suggested_action=p.suggested_action,
        tool=p.tool,
        confidence=p.confidence,
        priority=p.priority,
        status=p.status,
        entity_ids=p.entity_ids or [],
        context_snapshot=p.context_snapshot or {},
        delegation_id=p.delegation_id,
        created_at=p.created_at,
    )


@router.get("/proposals", response_model=list[ProposalResponse])
async def list_proposals(
    status: str | None = Query(None),
    pattern_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ProposalResponse]:
    """List agent proposals for the current org."""
    query = select(AgentProposal).where(AgentProposal.org_id == ctx.org_id)

    if status:
        query = query.where(AgentProposal.status == status)
    if pattern_type:
        query = query.where(AgentProposal.pattern_type == pattern_type)

    query = query.order_by(AgentProposal.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [_proposal_to_response(p) for p in result.scalars().all()]


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalResponse)
async def approve_proposal(
    proposal_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ProposalResponse:
    """Approve an agent proposal — creates a delegation for execution."""
    proposal = await record_feedback(
        proposal_id=proposal_id,
        action="approve",
        user_id=ctx.user_id,
        org_id=ctx.org_id,
        db=db,
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _proposal_to_response(proposal)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalResponse)
async def reject_proposal(
    proposal_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ProposalResponse:
    """Reject an agent proposal — trains the learner to reduce similar proposals."""
    proposal = await record_feedback(
        proposal_id=proposal_id,
        action="reject",
        user_id=ctx.user_id,
        org_id=ctx.org_id,
        db=db,
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _proposal_to_response(proposal)


@router.post("/proposals/{proposal_id}/dismiss", response_model=ProposalResponse)
async def dismiss_proposal(
    proposal_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ProposalResponse:
    """Dismiss a proposal without affecting learning (neutral signal)."""
    proposal = await record_feedback(
        proposal_id=proposal_id,
        action="dismiss",
        user_id=ctx.user_id,
        org_id=ctx.org_id,
        db=db,
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _proposal_to_response(proposal)


# ── Manual trigger ──

@router.post("/scan")
async def trigger_scan(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger the agent observe → plan pipeline for the current org."""
    # Check if agent is enabled
    config_result = await db.execute(
        select(AgentConfig).where(AgentConfig.org_id == ctx.org_id)
    )
    config = config_result.scalar_one_or_none()
    enabled_patterns = (config.patterns_enabled if config else None) or None

    # Observe
    observations = await observe(ctx.org_id, db, enabled_patterns=enabled_patterns)

    # Plan
    proposals = await plan(observations, ctx.org_id, db)

    return {
        "observations_found": len(observations),
        "proposals_created": len(proposals),
        "proposals": [_proposal_to_response(p) for p in proposals],
    }


# ── Stats ──

@router.get("/stats")
async def agent_stats(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return agent statistics including proposal counts, learning data, and config."""
    # Proposal counts by status
    result = await db.execute(
        select(AgentProposal.status, func.count(AgentProposal.id))
        .where(AgentProposal.org_id == ctx.org_id)
        .group_by(AgentProposal.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    # Counts by pattern type
    result = await db.execute(
        select(AgentProposal.pattern_type, func.count(AgentProposal.id))
        .where(AgentProposal.org_id == ctx.org_id)
        .group_by(AgentProposal.pattern_type)
    )
    pattern_counts = {row[0]: row[1] for row in result.all()}

    # Learning summary
    learning = await get_learning_summary(ctx.org_id, db)

    total = sum(status_counts.values())
    approved = status_counts.get("approved", 0) + status_counts.get("executed", 0)

    return {
        "total_proposals": total,
        "by_status": status_counts,
        "by_pattern": pattern_counts,
        "approval_rate": round(approved / total * 100, 1) if total > 0 else 0.0,
        "learning": learning,
    }


# ── Config ──

@router.get("/config", response_model=AgentConfigResponse)
async def get_config(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> AgentConfigResponse:
    """Get the agent configuration for the current org."""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.org_id == ctx.org_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        # Return defaults
        return AgentConfigResponse(
            enabled=True,
            mode="balanced",
            confidence_threshold=0.6,
            auto_approve_threshold=0.95,
            patterns_enabled=["stale_pr", "blocked_ticket", "missed_deadline", "unreviewed_pr", "idle_sprint_item"],
        )
    return AgentConfigResponse(
        enabled=config.enabled,
        mode=config.mode,
        confidence_threshold=config.confidence_threshold,
        auto_approve_threshold=config.auto_approve_threshold,
        patterns_enabled=config.patterns_enabled or [],
    )


@router.put("/config", response_model=AgentConfigResponse)
async def update_config(
    update: AgentConfigUpdate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> AgentConfigResponse:
    """Update agent configuration. Only owner/admin can modify."""
    ctx.require_role("owner", "admin")

    result = await db.execute(
        select(AgentConfig).where(AgentConfig.org_id == ctx.org_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = AgentConfig(org_id=ctx.org_id)
        db.add(config)

    if update.enabled is not None:
        config.enabled = update.enabled
    if update.mode is not None:
        config.mode = update.mode
    if update.confidence_threshold is not None:
        config.confidence_threshold = max(0.1, min(1.0, update.confidence_threshold))
    if update.auto_approve_threshold is not None:
        config.auto_approve_threshold = max(0.5, min(1.0, update.auto_approve_threshold))
    if update.patterns_enabled is not None:
        config.patterns_enabled = update.patterns_enabled

    await db.flush()

    return AgentConfigResponse(
        enabled=config.enabled,
        mode=config.mode,
        confidence_threshold=config.confidence_threshold,
        auto_approve_threshold=config.auto_approve_threshold,
        patterns_enabled=config.patterns_enabled or [],
    )
