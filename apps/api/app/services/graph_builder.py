"""Graph builder — extracts entity relationships from synced content.

After sync, this module scans entities for cross-references:
- Jira issue keys (PROJ-123) mentioned in GitHub PRs, Confluence pages, Slack messages
- GitHub PR/issue refs (#123, owner/repo#123) in Jira comments, Confluence pages
- Confluence page links in Jira descriptions
- Person mentions (@user, emails) across entities
- Shared labels/tags across tools

These relationships populate the EntityRelation table, enabling GraphRAG:
when a user asks "what's blocking the sprint?", we don't just vector-search —
we also traverse the entity graph to find connected context.
"""

import logging
import re
import uuid
from typing import Any

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEntity, EntityRelation

logger = logging.getLogger(__name__)

# ── Reference patterns ──

# Jira: PROJ-123, ABC-4567
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d{1,6})\b")

# GitHub: #123, owner/repo#123
GITHUB_REF_RE = re.compile(r"(?:([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+))?#(\d{1,6})\b")

# Confluence page IDs in URLs
CONFLUENCE_PAGE_RE = re.compile(r"confluence:page:(\d+)")

# Email-style mentions
EMAIL_RE = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")

# Relation types
REL_MENTIONS = "mentions"
REL_BLOCKS = "blocks"
REL_RELATED = "related_to"
REL_AUTHORED_BY = "authored_by"
REL_SAME_SPRINT = "same_sprint"
REL_SAME_LABEL = "same_label"
REL_COMMENT_ON = "comment_on"


async def build_relations_for_entity(
    entity: ContextEntity,
    db: AsyncSession,
) -> int:
    """Extract and store relations from a single entity to other entities in the same org.

    Returns the number of relations created.
    """
    text = f"{entity.title or ''}\n{entity.content or ''}"
    extra = entity.extra_data or {}
    source_integration = extra.get("source_integration", "")
    org_id = entity.org_id
    created = 0

    # Collect candidate source_ids to link to
    targets: list[tuple[str, str]] = []  # (source_id_pattern, relation_type)

    # 1. Jira issue keys mentioned in text
    for m in JIRA_KEY_RE.finditer(text):
        key = m.group(1)
        # Don't self-link: skip if this entity IS that Jira issue
        if entity.source_id and entity.source_id == f"jira:issue:{key}":
            continue
        targets.append((f"jira:issue:{key}", REL_MENTIONS))

    # 2. GitHub issue/PR refs
    for m in GITHUB_REF_RE.finditer(text):
        repo = m.group(1)
        num = m.group(2)
        if repo:
            # Full ref: owner/repo#123
            for kind in ("issue", "pr"):
                sid = f"github:{kind}:{repo}#{num}"
                if entity.source_id != sid:
                    targets.append((sid, REL_MENTIONS))
        else:
            # Bare #123 — only match within same repo context
            if source_integration == "github" and extra.get("type") in ("issue", "pr", "repository"):
                # Try to infer repo from title like "[repo-name] #123 ..."
                repo_match = re.match(r"\[([^\]]+)\]", entity.title or "")
                if repo_match:
                    repo_name = repo_match.group(1)
                    for kind in ("issue", "pr"):
                        sid = f"github:{kind}:{repo_name}#{num}"
                        if entity.source_id != sid:
                            targets.append((sid, REL_MENTIONS))

    # 3. Confluence page references
    for m in CONFLUENCE_PAGE_RE.finditer(text):
        page_id = m.group(1)
        sid = f"confluence:page:{page_id}"
        if entity.source_id != sid:
            targets.append((sid, REL_MENTIONS))

    # 4. Comment-on relationships (comments reference their parent)
    if extra.get("type") == "comment" and extra.get("page_id"):
        targets.append((f"confluence:page:{extra['page_id']}", REL_COMMENT_ON))

    # 5. Same-sprint relationships
    sprint_name = extra.get("sprint")
    if sprint_name and source_integration == "jira":
        # Find other entities in the same sprint
        sprint_peers = await _find_entities_by_extra(
            db, org_id, "sprint", sprint_name, exclude_id=entity.id
        )
        for peer_id in sprint_peers:
            targets.append((_ENTITY_ID_MARKER + str(peer_id), REL_SAME_SPRINT))

    # 6. Same-label relationships (shared labels across tools)
    labels = extra.get("labels", [])
    if labels and isinstance(labels, list):
        for label in labels[:5]:  # limit to 5 labels
            label_peers = await _find_entities_by_extra(
                db, org_id, "labels", label, exclude_id=entity.id, array_field=True
            )
            for peer_id in label_peers[:10]:  # limit fanout
                targets.append((_ENTITY_ID_MARKER + str(peer_id), REL_SAME_LABEL))

    # Resolve targets to actual entity IDs and create relations
    for target_ref, rel_type in targets:
        target_id = None

        if target_ref.startswith(_ENTITY_ID_MARKER):
            # Direct entity ID
            target_id = uuid.UUID(target_ref[len(_ENTITY_ID_MARKER):])
        else:
            # Look up by source_id
            result = await db.execute(
                select(ContextEntity.id).where(
                    ContextEntity.org_id == org_id,
                    ContextEntity.source_id == target_ref,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                target_id = row

        if target_id and target_id != entity.id:
            # Avoid duplicate relations
            exists = await db.execute(
                select(EntityRelation.id).where(
                    EntityRelation.org_id == org_id,
                    EntityRelation.source_entity_id == entity.id,
                    EntityRelation.target_entity_id == target_id,
                    EntityRelation.relation_type == rel_type,
                )
            )
            if not exists.scalar_one_or_none():
                db.add(EntityRelation(
                    org_id=org_id,
                    source_entity_id=entity.id,
                    target_entity_id=target_id,
                    relation_type=rel_type,
                    extra_data={"source_integration": source_integration},
                ))
                created += 1

    if created:
        await db.flush()

    return created


_ENTITY_ID_MARKER = "__eid__:"


async def _find_entities_by_extra(
    db: AsyncSession,
    org_id: uuid.UUID,
    field: str,
    value: str,
    exclude_id: uuid.UUID,
    array_field: bool = False,
    limit: int = 20,
) -> list[uuid.UUID]:
    """Find entities in the same org where extra_data[field] matches value."""
    from sqlalchemy import cast, String
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

    if array_field:
        # For array fields like "labels": check if value is in the array
        stmt = (
            select(ContextEntity.id)
            .where(
                ContextEntity.org_id == org_id,
                ContextEntity.id != exclude_id,
                ContextEntity.extra_data["labels"].astext.contains(value),
            )
            .limit(limit)
        )
    else:
        stmt = (
            select(ContextEntity.id)
            .where(
                ContextEntity.org_id == org_id,
                ContextEntity.id != exclude_id,
                ContextEntity.extra_data[field].astext == value,
            )
            .limit(limit)
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def build_relations_for_org(
    org_id: uuid.UUID,
    db: AsyncSession,
    batch_size: int = 100,
) -> int:
    """Rebuild all entity relations for an org. Used for full re-indexing."""
    # Clear existing relations
    await db.execute(
        delete(EntityRelation).where(EntityRelation.org_id == org_id)
    )
    await db.flush()

    total = 0
    offset = 0

    while True:
        result = await db.execute(
            select(ContextEntity)
            .where(ContextEntity.org_id == org_id)
            .order_by(ContextEntity.created_at)
            .offset(offset)
            .limit(batch_size)
        )
        entities = result.scalars().all()
        if not entities:
            break

        for entity in entities:
            count = await build_relations_for_entity(entity, db)
            total += count

        offset += batch_size

    logger.info("Built %d relations for org %s", total, org_id)
    return total


async def get_entity_neighbors(
    entity_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
    depth: int = 1,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get neighboring entities (1 or 2 hops) for GraphRAG context expansion.

    Returns list of dicts with entity info + relation metadata.
    """
    visited: set[uuid.UUID] = {entity_id}
    neighbors: list[dict[str, Any]] = []

    current_ids = [entity_id]

    for hop in range(depth):
        if not current_ids:
            break

        # Find relations where current entities are source OR target
        from sqlalchemy import or_
        result = await db.execute(
            select(EntityRelation)
            .where(
                EntityRelation.org_id == org_id,
                or_(
                    EntityRelation.source_entity_id.in_(current_ids),
                    EntityRelation.target_entity_id.in_(current_ids),
                ),
            )
            .limit(limit)
        )
        relations = result.scalars().all()

        next_ids: list[uuid.UUID] = []
        for rel in relations:
            # Determine the neighbor (the entity on the other side)
            neighbor_id = (
                rel.target_entity_id
                if rel.source_entity_id in visited
                else rel.source_entity_id
            )
            if neighbor_id in visited:
                continue

            visited.add(neighbor_id)
            next_ids.append(neighbor_id)
            neighbors.append({
                "entity_id": str(neighbor_id),
                "relation_type": rel.relation_type,
                "hop": hop + 1,
                "relation_extra": rel.extra_data or {},
            })

        current_ids = next_ids

    # Enrich with entity details
    if neighbors:
        neighbor_ids = [uuid.UUID(n["entity_id"]) for n in neighbors]
        result = await db.execute(
            select(ContextEntity).where(ContextEntity.id.in_(neighbor_ids))
        )
        entity_map = {str(e.id): e for e in result.scalars().all()}

        for n in neighbors:
            entity = entity_map.get(n["entity_id"])
            if entity:
                n["entity_type"] = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
                n["title"] = entity.title
                n["content"] = (entity.content or "")[:300]
                n["source_url"] = entity.source_url
                n["source_integration"] = (entity.extra_data or {}).get("source_integration", "")

    return neighbors


async def get_graph_for_org(
    org_id: uuid.UUID,
    db: AsyncSession,
    limit_nodes: int = 200,
    limit_edges: int = 500,
) -> dict[str, Any]:
    """Get the full knowledge graph for visualization.

    Returns { nodes: [...], edges: [...] } suitable for force-graph rendering.
    """
    # Fetch entities (nodes)
    result = await db.execute(
        select(ContextEntity)
        .where(ContextEntity.org_id == org_id)
        .order_by(ContextEntity.updated_at.desc())
        .limit(limit_nodes)
    )
    entities = result.scalars().all()
    entity_ids = {e.id for e in entities}

    nodes = []
    for e in entities:
        extra = e.extra_data or {}
        nodes.append({
            "id": str(e.id),
            "title": e.title,
            "entity_type": e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type),
            "source_integration": extra.get("source_integration", ""),
            "source_url": e.source_url,
            "content_preview": (e.content or "")[:150],
            "extra": {
                k: v for k, v in extra.items()
                if k in ("status", "priority", "sprint", "labels", "type", "assignee", "project")
            },
        })

    # Fetch relations (edges) between those entities
    from sqlalchemy import or_
    result = await db.execute(
        select(EntityRelation)
        .where(
            EntityRelation.org_id == org_id,
            EntityRelation.source_entity_id.in_(entity_ids),
            EntityRelation.target_entity_id.in_(entity_ids),
        )
        .limit(limit_edges)
    )
    relations = result.scalars().all()

    edges = []
    for r in relations:
        edges.append({
            "source": str(r.source_entity_id),
            "target": str(r.target_entity_id),
            "relation_type": r.relation_type,
        })

    return {"nodes": nodes, "edges": edges}
