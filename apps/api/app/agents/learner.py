"""LearnerAgent — tracks approval/rejection signals to improve proposal confidence.

When a proposal is approved or rejected, the learner:
1. Updates the per-pattern approval statistics in AgentConfig.learning_data
2. Adjusts confidence thresholds based on rolling approval rates
3. Provides the compute_confidence function used by the PlannerAgent

Learning data schema (stored in AgentConfig.learning_data):
{
    "stale_pr": {"total": 20, "approved": 15, "rejected": 5, "approval_rate": 0.75},
    "blocked_ticket": {"total": 10, "approved": 9, "rejected": 1, "approval_rate": 0.90},
    ...
}
"""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentProposal, AgentConfig, Delegation, DelegationStatus

logger = logging.getLogger(__name__)


async def record_feedback(
    proposal_id: uuid.UUID,
    action: str,  # "approve" | "reject" | "dismiss"
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> AgentProposal | None:
    """Record user feedback on a proposal and update learning data.

    If approved, creates a Delegation for the execution engine.
    Returns the updated proposal.
    """
    result = await db.execute(
        select(AgentProposal).where(
            AgentProposal.id == proposal_id,
            AgentProposal.org_id == org_id,
        )
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        return None

    if proposal.status != "pending":
        return proposal  # Already resolved

    # Update proposal status
    if action == "approve":
        proposal.status = "approved"
    elif action == "reject":
        proposal.status = "rejected"
    elif action == "dismiss":
        proposal.status = "dismissed"
    else:
        return proposal

    proposal.resolved_by_user_id = user_id
    proposal.resolved_at = datetime.now(UTC)

    # If approved, create a Delegation for the execution engine
    if action == "approve":
        delegation = Delegation(
            org_id=org_id,
            action=proposal.suggested_action,
            reason=f"Agent proposal: {proposal.description}",
            tool=proposal.tool,
            confidence=proposal.confidence,
            status=DelegationStatus.APPROVED,
            proposed_for_user_id=user_id,
            resolved_by_user_id=user_id,
            resolved_at=datetime.now(UTC),
        )
        db.add(delegation)
        await db.flush()
        proposal.delegation_id = delegation.id

    # Update learning data (skip for dismissals — those are neutral)
    if action in ("approve", "reject"):
        await _update_learning_data(
            org_id=org_id,
            pattern_type=proposal.pattern_type,
            was_approved=(action == "approve"),
            db=db,
        )

    await db.flush()
    return proposal


async def _update_learning_data(
    org_id: uuid.UUID,
    pattern_type: str,
    was_approved: bool,
    db: AsyncSession,
) -> None:
    """Update per-pattern approval stats in AgentConfig.learning_data."""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.org_id == org_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        # Auto-create config on first feedback
        config = AgentConfig(org_id=org_id)
        db.add(config)
        await db.flush()

    learning_data = dict(config.learning_data or {})
    pattern_stats = learning_data.get(pattern_type, {
        "total": 0,
        "approved": 0,
        "rejected": 0,
        "approval_rate": 0.5,
    })

    pattern_stats["total"] = pattern_stats.get("total", 0) + 1
    if was_approved:
        pattern_stats["approved"] = pattern_stats.get("approved", 0) + 1
    else:
        pattern_stats["rejected"] = pattern_stats.get("rejected", 0) + 1

    total = pattern_stats["total"]
    if total > 0:
        pattern_stats["approval_rate"] = round(pattern_stats["approved"] / total, 3)

    learning_data[pattern_type] = pattern_stats
    config.learning_data = learning_data

    logger.info(
        "Learner: updated %s — total=%d, approved=%d, rate=%.2f",
        pattern_type,
        pattern_stats["total"],
        pattern_stats["approved"],
        pattern_stats["approval_rate"],
    )


async def get_learning_summary(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Return a summary of the learning state for an org."""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.org_id == org_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"patterns": {}, "total_feedback": 0, "overall_approval_rate": 0.0}

    learning_data = config.learning_data or {}
    total_fb = sum(p.get("total", 0) for p in learning_data.values())
    total_approved = sum(p.get("approved", 0) for p in learning_data.values())

    return {
        "patterns": learning_data,
        "total_feedback": total_fb,
        "overall_approval_rate": round(total_approved / total_fb, 3) if total_fb > 0 else 0.0,
        "confidence_threshold": config.confidence_threshold,
        "mode": config.mode,
        "enabled": config.enabled,
    }
