"""Data retention service — enforce retention policies on context entities and audit logs.

Provides:
  - Entity retention: delete context entities (and their Weaviate vectors) older than N days
  - Audit log retention: delete audit logs older than N days (configurable per org)
  - Orphan cleanup: remove entity relations pointing to deleted entities
"""

import logging
import uuid
from datetime import datetime, UTC, timedelta

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEntity, EntityRelation, AuditLog

logger = logging.getLogger(__name__)

# Default retention periods (days)
DEFAULT_ENTITY_RETENTION_DAYS = 90
DEFAULT_AUDIT_RETENTION_DAYS = 365


async def purge_old_entities(
    org_id: uuid.UUID,
    db: AsyncSession,
    retention_days: int = DEFAULT_ENTITY_RETENTION_DAYS,
) -> dict:
    """Delete context entities older than retention_days for an org.

    Returns: {"entities_deleted": int, "relations_cleaned": int}
    """
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    # Find entities to delete
    result = await db.execute(
        select(ContextEntity.id).where(
            ContextEntity.org_id == org_id,
            ContextEntity.updated_at < cutoff,
        )
    )
    entity_ids = [row[0] for row in result.all()]

    if not entity_ids:
        return {"entities_deleted": 0, "relations_cleaned": 0}

    # Delete relations referencing these entities
    rel_result = await db.execute(
        delete(EntityRelation).where(
            (EntityRelation.source_entity_id.in_(entity_ids))
            | (EntityRelation.target_entity_id.in_(entity_ids))
        )
    )
    relations_cleaned = rel_result.rowcount or 0

    # Delete entities
    ent_result = await db.execute(
        delete(ContextEntity).where(ContextEntity.id.in_(entity_ids))
    )
    entities_deleted = ent_result.rowcount or 0

    # Best-effort: remove from Weaviate too
    try:
        from app.services.context_engine import get_weaviate_client, COLLECTION_NAME
        client = get_weaviate_client()
        collection = client.collections.get(COLLECTION_NAME)
        for eid in entity_ids:
            try:
                from weaviate.classes.query import Filter
                collection.data.delete_many(
                    where=Filter.by_property("entity_id").equal(str(eid))
                )
            except Exception:
                pass
        client.close()
    except Exception:
        logger.debug("Weaviate cleanup skipped", exc_info=True)

    logger.info(
        "Retention: purged %d entities, %d relations for org %s (cutoff: %s)",
        entities_deleted, relations_cleaned, org_id, cutoff.isoformat(),
    )
    return {"entities_deleted": entities_deleted, "relations_cleaned": relations_cleaned}


async def purge_old_audit_logs(
    org_id: uuid.UUID,
    db: AsyncSession,
    retention_days: int = DEFAULT_AUDIT_RETENTION_DAYS,
) -> int:
    """Delete audit logs older than retention_days. Returns count deleted."""
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    result = await db.execute(
        delete(AuditLog).where(
            AuditLog.org_id == org_id,
            AuditLog.created_at < cutoff,
        )
    )
    deleted = result.rowcount or 0
    if deleted:
        logger.info("Retention: purged %d audit logs for org %s", deleted, org_id)
    return deleted


async def cleanup_orphan_relations(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Remove entity relations where source or target entity no longer exists."""
    # Find relation IDs where source or target is missing
    from sqlalchemy.orm import aliased
    source_alias = aliased(ContextEntity)
    target_alias = aliased(ContextEntity)

    # Delete relations with missing source
    result1 = await db.execute(
        delete(EntityRelation).where(
            EntityRelation.org_id == org_id,
            ~EntityRelation.source_entity_id.in_(
                select(ContextEntity.id).where(ContextEntity.org_id == org_id)
            ),
        )
    )

    # Delete relations with missing target
    result2 = await db.execute(
        delete(EntityRelation).where(
            EntityRelation.org_id == org_id,
            ~EntityRelation.target_entity_id.in_(
                select(ContextEntity.id).where(ContextEntity.org_id == org_id)
            ),
        )
    )

    total = (result1.rowcount or 0) + (result2.rowcount or 0)
    if total:
        logger.info("Retention: cleaned %d orphan relations for org %s", total, org_id)
    return total


async def get_retention_stats(
    org_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Return retention statistics for governance dashboard."""
    now = datetime.now(UTC)

    # Entity age distribution
    result = await db.execute(
        select(func.count(ContextEntity.id)).where(
            ContextEntity.org_id == org_id,
        )
    )
    total_entities = result.scalar() or 0

    result = await db.execute(
        select(func.count(ContextEntity.id)).where(
            ContextEntity.org_id == org_id,
            ContextEntity.updated_at < now - timedelta(days=30),
        )
    )
    entities_older_30d = result.scalar() or 0

    result = await db.execute(
        select(func.count(ContextEntity.id)).where(
            ContextEntity.org_id == org_id,
            ContextEntity.updated_at < now - timedelta(days=90),
        )
    )
    entities_older_90d = result.scalar() or 0

    result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.org_id == org_id)
    )
    total_audit_logs = result.scalar() or 0

    return {
        "total_entities": total_entities,
        "entities_older_30d": entities_older_30d,
        "entities_older_90d": entities_older_90d,
        "total_audit_logs": total_audit_logs,
        "entity_retention_days": DEFAULT_ENTITY_RETENTION_DAYS,
        "audit_retention_days": DEFAULT_AUDIT_RETENTION_DAYS,
    }
