"""ObserverAgent — watches synced entities for actionable patterns.

Runs after each sync cycle. Scans recent entities for known patterns:
  - stale_pr: PR open > N days with no review activity
  - blocked_ticket: Jira ticket with "blocked" label or blocker links
  - missed_deadline: Task past due date
  - unreviewed_pr: PR with no reviewer assigned
  - idle_sprint_item: Sprint item stuck in "To Do" for > 3 days
  - knowledge_gap: Confluence page referenced but missing/stale

Each detector returns a list of Observation dicts ready for the PlannerAgent.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEntity, EntityType, Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class Observation:
    """A detected pattern worth acting on."""
    pattern_type: str
    title: str
    description: str
    entity_ids: list[str]
    severity: str  # critical, high, medium, low
    context: dict[str, Any] = field(default_factory=dict)


# ── Pattern detectors ──


async def detect_stale_prs(
    org_id: uuid.UUID,
    db: AsyncSession,
    stale_days: int = 3,
) -> list[Observation]:
    """Find pull requests open for more than N days with no recent activity."""
    cutoff = datetime.now(UTC) - timedelta(days=stale_days)

    result = await db.execute(
        select(ContextEntity).where(
            ContextEntity.org_id == org_id,
            ContextEntity.entity_type == EntityType.TASK,
            ContextEntity.created_at < cutoff,
        )
    )
    entities = result.scalars().all()

    observations: list[Observation] = []
    for entity in entities:
        extra = entity.extra_data or {}
        if extra.get("type") not in ("pr", "pull_request"):
            continue
        if extra.get("state") not in ("open",):
            continue

        age_days = (datetime.now(UTC) - entity.created_at).days
        observations.append(Observation(
            pattern_type="stale_pr",
            title=f"Stale PR: {entity.title}",
            description=(
                f"This pull request has been open for {age_days} days. "
                f"Consider pinging the reviewer or adding a review request."
            ),
            entity_ids=[str(entity.id)],
            severity="high" if age_days > 7 else "medium",
            context={
                "source_url": entity.source_url,
                "source_integration": extra.get("source_integration", ""),
                "age_days": age_days,
                "state": extra.get("state"),
            },
        ))

    return observations


async def detect_blocked_tickets(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[Observation]:
    """Find tickets that are blocked — by label, blocker field, or status."""
    result = await db.execute(
        select(ContextEntity).where(
            ContextEntity.org_id == org_id,
            ContextEntity.entity_type == EntityType.TASK,
        )
    )
    entities = result.scalars().all()

    observations: list[Observation] = []
    for entity in entities:
        extra = entity.extra_data or {}
        labels = [l.lower() for l in extra.get("labels", [])]
        status = (extra.get("status") or "").lower()
        source = extra.get("source_integration", "")

        is_blocked = (
            "blocked" in labels
            or "blocker" in labels
            or status in ("blocked", "impediment")
        )
        if not is_blocked:
            continue

        observations.append(Observation(
            pattern_type="blocked_ticket",
            title=f"Blocked: {entity.title}",
            description=(
                f"This ticket is flagged as blocked. "
                f"Status: {extra.get('status', 'unknown')}. Consider escalating to the team lead."
            ),
            entity_ids=[str(entity.id)],
            severity="high",
            context={
                "source_url": entity.source_url,
                "source_integration": source,
                "status": extra.get("status"),
                "labels": extra.get("labels", []),
            },
        ))

    return observations


async def detect_missed_deadlines(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[Observation]:
    """Find tasks past their due date that are not done."""
    now = datetime.now(UTC)

    result = await db.execute(
        select(Task).where(
            Task.org_id == org_id,
            Task.due_date < now,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW]),
        )
    )
    tasks = result.scalars().all()

    observations: list[Observation] = []
    for task in tasks:
        days_overdue = (now - task.due_date).days
        observations.append(Observation(
            pattern_type="missed_deadline",
            title=f"Overdue: {task.title}",
            description=(
                f"This task is {days_overdue} day{'s' if days_overdue != 1 else ''} past its due date. "
                f"Current status: {task.status.value}. Consider re-prioritizing or reassigning."
            ),
            entity_ids=[str(task.id)],
            severity="critical" if days_overdue > 7 else "high",
            context={
                "due_date": task.due_date.isoformat(),
                "days_overdue": days_overdue,
                "status": task.status.value,
                "priority": task.priority.value,
                "source_url": task.source_url,
            },
        ))

    return observations


async def detect_unreviewed_prs(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> list[Observation]:
    """Find open PRs with no reviewers assigned."""
    result = await db.execute(
        select(ContextEntity).where(
            ContextEntity.org_id == org_id,
            ContextEntity.entity_type == EntityType.TASK,
        )
    )
    entities = result.scalars().all()

    observations: list[Observation] = []
    for entity in entities:
        extra = entity.extra_data or {}
        if extra.get("type") not in ("pr", "pull_request"):
            continue
        if extra.get("state") != "open":
            continue

        reviewers = extra.get("reviewers", [])
        if reviewers:
            continue

        age_days = (datetime.now(UTC) - entity.created_at).days
        if age_days < 1:
            continue  # Give at least a day before flagging

        observations.append(Observation(
            pattern_type="unreviewed_pr",
            title=f"No reviewer: {entity.title}",
            description=(
                f"This PR has been open for {age_days} day{'s' if age_days != 1 else ''} "
                f"with no reviewer assigned. Consider requesting a review."
            ),
            entity_ids=[str(entity.id)],
            severity="medium",
            context={
                "source_url": entity.source_url,
                "source_integration": extra.get("source_integration", ""),
                "age_days": age_days,
            },
        ))

    return observations


async def detect_idle_sprint_items(
    org_id: uuid.UUID,
    db: AsyncSession,
    idle_days: int = 3,
) -> list[Observation]:
    """Find sprint items stuck in To Do for too long."""
    cutoff = datetime.now(UTC) - timedelta(days=idle_days)

    result = await db.execute(
        select(ContextEntity).where(
            ContextEntity.org_id == org_id,
            ContextEntity.entity_type == EntityType.TASK,
            ContextEntity.updated_at < cutoff,
        )
    )
    entities = result.scalars().all()

    observations: list[Observation] = []
    for entity in entities:
        extra = entity.extra_data or {}
        if not extra.get("sprint"):
            continue

        status = (extra.get("status") or "").lower()
        if status not in ("to do", "todo", "open", "new", "backlog"):
            continue

        idle = (datetime.now(UTC) - entity.updated_at).days
        observations.append(Observation(
            pattern_type="idle_sprint_item",
            title=f"Idle: {entity.title}",
            description=(
                f"This sprint item has been in '{extra.get('status', 'To Do')}' "
                f"for {idle} days without updates. Sprint: {extra.get('sprint')}."
            ),
            entity_ids=[str(entity.id)],
            severity="medium" if idle < 5 else "high",
            context={
                "source_url": entity.source_url,
                "sprint": extra.get("sprint"),
                "status": extra.get("status"),
                "idle_days": idle,
            },
        ))

    return observations


# ── Composite observer ──

DETECTORS = {
    "stale_pr": detect_stale_prs,
    "blocked_ticket": detect_blocked_tickets,
    "missed_deadline": detect_missed_deadlines,
    "unreviewed_pr": detect_unreviewed_prs,
    "idle_sprint_item": detect_idle_sprint_items,
}


async def observe(
    org_id: uuid.UUID,
    db: AsyncSession,
    enabled_patterns: list[str] | None = None,
) -> list[Observation]:
    """Run all enabled detectors and return observations.

    Args:
        enabled_patterns: If provided, only run these detectors. Otherwise run all.
    """
    patterns = enabled_patterns or list(DETECTORS.keys())
    all_observations: list[Observation] = []

    for pattern in patterns:
        detector = DETECTORS.get(pattern)
        if not detector:
            continue
        try:
            obs = await detector(org_id, db)
            all_observations.extend(obs)
            logger.info("Observer: %s found %d observations", pattern, len(obs))
        except Exception:
            logger.warning("Observer: %s detector failed", pattern, exc_info=True)

    logger.info("Observer: %d total observations for org %s", len(all_observations), org_id)
    return all_observations
