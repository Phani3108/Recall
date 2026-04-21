import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.api.schemas import ContextEntityResponse, ContextSearchRequest, ContextSearchResponse
from app.db.models import ContextEntity
from app.db.session import get_db
from app.services.context_engine import hybrid_search

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=ContextSearchResponse)
async def search_context(
    req: ContextSearchRequest,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ContextSearchResponse:
    """Search the unified context graph via Weaviate hybrid search.

    Falls back to SQL text search if Weaviate is unavailable.
    """
    # Try Weaviate hybrid search first
    try:
        results = await hybrid_search(
            query=req.query,
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            entity_types=req.entity_types,
            limit=req.limit,
        )

        return ContextSearchResponse(
            results=[
                ContextEntityResponse(
                    id=uuid.UUID(r["entity_id"]),
                    entity_type=r.get("entity_type", "document"),
                    title=r["title"],
                    content=r.get("content", "")[:500] if r.get("content") else None,
                    source_url=r.get("source_url"),
                    metadata={"source_integration": r.get("source_integration", "")},
                    relevance_score=r.get("score"),
                    created_at=None,
                )
                for r in results
            ],
            total=len(results),
            query=req.query,
        )
    except Exception:
        logger.warning("Weaviate search failed, falling back to SQL", exc_info=True)

    # Fallback: SQL text search
    query = select(ContextEntity).where(
        ContextEntity.org_id == ctx.org_id,
        ContextEntity.title.ilike(f"%{req.query}%"),
    )

    if req.entity_types:
        query = query.where(ContextEntity.entity_type.in_(req.entity_types))

    query = query.where(
        (ContextEntity.access_everyone == True)  # noqa: E712
        | (ContextEntity.access_user_ids.contains([str(ctx.user_id)]))
    )

    query = query.limit(req.limit)
    result = await db.execute(query)
    entities = result.scalars().all()

    return ContextSearchResponse(
        results=[
            ContextEntityResponse(
                id=e.id,
                entity_type=e.entity_type.value,
                title=e.title,
                content=e.content[:500] if e.content else None,
                source_url=e.source_url,
                metadata=e.extra_data,
                relevance_score=None,
                created_at=e.created_at,
            )
            for e in entities
        ],
        total=len(entities),
        query=req.query,
    )
