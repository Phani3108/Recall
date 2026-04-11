"""Knowledge graph routes — entity graph visualization and exploration."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_org_context, OrgContext
from app.services.graph_builder import get_graph_for_org, get_entity_neighbors, build_relations_for_org

router = APIRouter()


@router.get("/graph")
async def get_knowledge_graph(
    limit_nodes: int = Query(default=200, ge=10, le=500),
    limit_edges: int = Query(default=500, ge=10, le=2000),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the full knowledge graph for visualization.

    Returns nodes (entities) and edges (relations) for force-graph rendering.
    """
    graph = await get_graph_for_org(
        org_id=ctx.org_id,
        db=db,
        limit_nodes=limit_nodes,
        limit_edges=limit_edges,
    )
    return graph


@router.get("/graph/entity/{entity_id}/neighbors")
async def get_entity_graph_neighbors(
    entity_id: uuid.UUID,
    depth: int = Query(default=1, ge=1, le=3),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get neighbors of a specific entity in the knowledge graph."""
    neighbors = await get_entity_neighbors(
        entity_id=entity_id,
        org_id=ctx.org_id,
        db=db,
        depth=depth,
        limit=50,
    )
    return {"entity_id": str(entity_id), "neighbors": neighbors, "count": len(neighbors)}


@router.post("/graph/rebuild")
async def rebuild_knowledge_graph(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rebuild all entity relationships for the organization.

    This re-scans all entities and extracts cross-references.
    """
    ctx.require_role("owner", "admin")
    total = await build_relations_for_org(org_id=ctx.org_id, db=db)
    return {"status": "ok", "relations_created": total}


@router.get("/graph/stats")
async def graph_stats(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get knowledge graph statistics."""
    from sqlalchemy import select, func
    from app.db.models import ContextEntity, EntityRelation

    # Count nodes
    node_result = await db.execute(
        select(func.count(ContextEntity.id)).where(ContextEntity.org_id == ctx.org_id)
    )
    node_count = node_result.scalar() or 0

    # Count edges
    edge_result = await db.execute(
        select(func.count(EntityRelation.id)).where(EntityRelation.org_id == ctx.org_id)
    )
    edge_count = edge_result.scalar() or 0

    # Count by entity type
    type_result = await db.execute(
        select(ContextEntity.entity_type, func.count(ContextEntity.id))
        .where(ContextEntity.org_id == ctx.org_id)
        .group_by(ContextEntity.entity_type)
    )
    type_counts = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
        for row in type_result.all()
    }

    # Count by relation type
    rel_result = await db.execute(
        select(EntityRelation.relation_type, func.count(EntityRelation.id))
        .where(EntityRelation.org_id == ctx.org_id)
        .group_by(EntityRelation.relation_type)
    )
    rel_counts = {row[0]: row[1] for row in rel_result.all()}

    # Count by source integration
    source_result = await db.execute(
        select(
            ContextEntity.extra_data["source_integration"].astext,
            func.count(ContextEntity.id),
        )
        .where(ContextEntity.org_id == ctx.org_id)
        .group_by(ContextEntity.extra_data["source_integration"].astext)
    )
    source_counts = {row[0]: row[1] for row in source_result.all() if row[0]}

    return {
        "total_nodes": node_count,
        "total_edges": edge_count,
        "nodes_by_type": type_counts,
        "edges_by_relation": rel_counts,
        "nodes_by_source": source_counts,
    }
