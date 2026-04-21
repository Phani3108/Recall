"""PlannerAgent — converts observations into actionable proposals with confidence scores.

For each observation from the ObserverAgent, the planner:
1. Checks if a similar proposal already exists (dedup)
2. Determines the best action and target tool
3. Applies learned confidence adjustments from the LearnerAgent
4. Creates an AgentProposal record

When an LLM is available, uses it to generate natural-language action descriptions.
Falls back to template-based generation when in mock mode.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.observer import Observation
from app.db.models import AgentConfig, AgentProposal

logger = logging.getLogger(__name__)


# ── Action templates per pattern type ──

ACTION_TEMPLATES: dict[str, dict] = {
    "stale_pr": {
        "tool": "github",
        "action_template": "Comment on {title}: \"This PR has been open for {age_days} days. @reviewers — please review or let us know if it's blocked.\"",
        "priority": "high",
    },
    "blocked_ticket": {
        "tool": "jira",
        "action_template": "Comment on {title}: \"This ticket is blocked. Escalating for team lead attention. Current status: {status}.\"",
        "priority": "high",
    },
    "missed_deadline": {
        "tool": "jira",
        "action_template": "Comment on {title}: \"This task is {days_overdue} days overdue (due: {due_date}). Please update the status or adjust the deadline.\"",
        "priority": "critical",
    },
    "unreviewed_pr": {
        "tool": "github",
        "action_template": "Request review on {title} from a team member. PR has been open {age_days} days with no reviewer.",
        "priority": "medium",
    },
    "idle_sprint_item": {
        "tool": "jira",
        "action_template": "Comment on {title}: \"This sprint item has been idle for {idle_days} days in '{status}'. Sprint: {sprint}. Does it need to be re-scoped or reassigned?\"",
        "priority": "medium",
    },
    "knowledge_gap": {
        "tool": "confluence",
        "action_template": "Create or update documentation for {title} — referenced in code/tickets but no Confluence page exists.",
        "priority": "low",
    },
}

# Base confidence per pattern type (may be adjusted by learner)
BASE_CONFIDENCE: dict[str, float] = {
    "stale_pr": 0.75,
    "blocked_ticket": 0.80,
    "missed_deadline": 0.85,
    "unreviewed_pr": 0.70,
    "idle_sprint_item": 0.65,
    "knowledge_gap": 0.50,
}


def generate_action(observation: Observation) -> tuple[str, str, str]:
    """Generate (suggested_action, tool, priority) from an observation using templates.

    Returns action text, tool name, priority string.
    """
    template = ACTION_TEMPLATES.get(observation.pattern_type)
    if not template:
        return (
            f"Review: {observation.title}. {observation.description}",
            "jira",
            observation.severity,
        )

    # Build template context from observation
    ctx = {
        "title": observation.title,
        **observation.context,
    }
    try:
        action = template["action_template"].format(**ctx)
    except KeyError:
        action = template["action_template"].format(title=observation.title)

    return action, template["tool"], template.get("priority", observation.severity)


async def get_agent_config(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> AgentConfig | None:
    """Fetch or return None for the org's agent config."""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def _dedup_check(
    org_id: uuid.UUID,
    pattern_type: str,
    entity_ids: list[str],
    db: AsyncSession,
) -> bool:
    """Return True if a similar pending proposal already exists (skip creation)."""
    recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
    result = await db.execute(
        select(AgentProposal).where(
            AgentProposal.org_id == org_id,
            AgentProposal.pattern_type == pattern_type,
            AgentProposal.status.in_(["pending", "approved"]),
            AgentProposal.created_at > recent_cutoff,
        )
    )
    existing = result.scalars().all()

    # Check for overlapping entity IDs
    new_ids = set(entity_ids)
    for proposal in existing:
        existing_ids = set(proposal.entity_ids or [])
        if new_ids & existing_ids:
            return True

    return False


def compute_confidence(
    observation: Observation,
    learning_data: dict,
) -> float:
    """Compute confidence score for a proposal, adjusted by historical learning data.

    learning_data shape:
    {
        "pattern_type": {
            "total": int,
            "approved": int,
            "rejected": int,
            "approval_rate": float,
        }
    }
    """
    base = BASE_CONFIDENCE.get(observation.pattern_type, 0.5)

    # Adjust based on historical approval rate
    pattern_stats = learning_data.get(observation.pattern_type, {})
    total = pattern_stats.get("total", 0)
    if total >= 5:  # Need at least 5 data points
        approval_rate = pattern_stats.get("approval_rate", 0.5)
        # Blend base confidence with learned rate (weighted toward learned as data grows)
        weight = min(total / 50, 0.8)  # Max 80% weight for learned data
        base = base * (1 - weight) + approval_rate * weight

    # Severity boost
    severity_boost = {
        "critical": 0.10,
        "high": 0.05,
        "medium": 0.0,
        "low": -0.05,
    }
    base += severity_boost.get(observation.severity, 0.0)

    return round(max(0.1, min(0.99, base)), 3)


async def plan(
    observations: list[Observation],
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[AgentProposal]:
    """Convert observations into proposals, applying dedup, confidence, and thresholds.

    Returns list of newly created AgentProposal records.
    """
    # Load agent config
    config = await get_agent_config(org_id, db)
    if config and not config.enabled:
        logger.info("Agent disabled for org %s, skipping planning", org_id)
        return []

    confidence_threshold = config.confidence_threshold if config else 0.6
    learning_data = (config.learning_data if config else {}) or {}
    enabled_patterns = (config.patterns_enabled if config else None) or list(ACTION_TEMPLATES.keys())

    proposals: list[AgentProposal] = []

    for obs in observations:
        # Filter by enabled patterns
        if obs.pattern_type not in enabled_patterns:
            continue

        # Dedup
        is_dup = await _dedup_check(org_id, obs.pattern_type, obs.entity_ids, db)
        if is_dup:
            logger.debug("Skipping duplicate proposal for %s", obs.title)
            continue

        # Generate action
        action_text, tool, priority = generate_action(obs)

        # Compute confidence
        confidence = compute_confidence(obs, learning_data)
        if confidence < confidence_threshold:
            logger.debug(
                "Skipping low-confidence proposal: %s (%.2f < %.2f)",
                obs.title, confidence, confidence_threshold,
            )
            continue

        # Create proposal
        proposal = AgentProposal(
            org_id=org_id,
            pattern_type=obs.pattern_type,
            title=obs.title,
            description=obs.description,
            suggested_action=action_text,
            tool=tool,
            confidence=confidence,
            priority=priority,
            status="pending",
            entity_ids=obs.entity_ids,
            context_snapshot=obs.context,
        )
        db.add(proposal)
        proposals.append(proposal)

    if proposals:
        await db.flush()
        logger.info("Planner: created %d proposals for org %s", len(proposals), org_id)

    return proposals
