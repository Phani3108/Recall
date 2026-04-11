"""Weaviate context engine — embedding pipeline and hybrid search.

This is the core moat: a unified knowledge graph that makes AI effective
across all enterprise tools by providing relevant, permission-filtered context.
"""

from __future__ import annotations

import uuid
import hashlib
import logging
from typing import Any, TYPE_CHECKING

import httpx

from app.config import settings

if TYPE_CHECKING:
    import weaviate

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ContextEntity"


def _import_weaviate():
    """Lazy import of weaviate to avoid slow startup."""
    import weaviate as _weaviate
    return _weaviate


# ── Embedding via LiteLLM proxy ──


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector from LiteLLM proxy (routes to configured model)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.litellm_proxy_url}/embeddings",
            headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
            json={
                "model": "text-embedding-3-small",
                "input": text,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embedding for multiple texts."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.litellm_proxy_url}/embeddings",
            headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
            json={
                "model": "text-embedding-3-small",
                "input": texts,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


# ── Weaviate client management ──


def get_weaviate_client():
    """Create a Weaviate client connection."""
    weaviate = _import_weaviate()
    client = weaviate.connect_to_local(
        host=settings.weaviate_url.replace("http://", "").split(":")[0],
        port=int(settings.weaviate_url.split(":")[-1]) if ":" in settings.weaviate_url.rsplit("//", 1)[-1] else 8080,
    )
    return client


async def ensure_collection_exists() -> None:
    """Create the ContextEntity collection in Weaviate if it doesn't exist."""
    from weaviate.classes.config import Configure, Property, DataType, VectorDistances

    client = get_weaviate_client()
    try:
        if not client.collections.exists(COLLECTION_NAME):
            client.collections.create(
                name=COLLECTION_NAME,
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                ),
                properties=[
                    Property(name="entity_id", data_type=DataType.TEXT),
                    Property(name="org_id", data_type=DataType.TEXT),
                    Property(name="entity_type", data_type=DataType.TEXT),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="source_integration", data_type=DataType.TEXT),
                    Property(name="source_url", data_type=DataType.TEXT),
                    Property(name="access_everyone", data_type=DataType.BOOL),
                    Property(name="access_user_ids", data_type=DataType.TEXT_ARRAY),
                    Property(name="chunk_index", data_type=DataType.INT),
                    Property(name="content_hash", data_type=DataType.TEXT),
                ],
            )
            logger.info("Created Weaviate collection: %s", COLLECTION_NAME)
    finally:
        client.close()


# ── Chunking ──


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Uses paragraph boundaries where possible, falls back to sentence/char splits.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If single paragraph is too long, split by sentences
            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_chars:
                        current_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    # Add overlap between chunks
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{prev_tail} {chunks[i]}")
        chunks = overlapped

    return chunks


# ── Index / Upsert ──


async def index_entity(
    entity_id: uuid.UUID,
    org_id: uuid.UUID,
    entity_type: str,
    title: str,
    content: str,
    source_integration: str | None = None,
    source_url: str | None = None,
    access_everyone: bool = False,
    access_user_ids: list[str] | None = None,
) -> list[str]:
    """Index an entity into Weaviate with chunked embeddings.

    Returns list of Weaviate object UUIDs for the chunks.
    """
    full_text = f"{title}\n\n{content}" if content else title
    chunks = chunk_text(full_text)

    # Get embeddings for all chunks in batch
    try:
        embeddings = await get_embeddings_batch(chunks)
    except Exception:
        logger.warning("Embedding failed for entity %s, indexing without vectors", entity_id)
        embeddings = [None] * len(chunks)

    client = get_weaviate_client()
    vector_ids: list[str] = []

    try:
        collection = client.collections.get(COLLECTION_NAME)

        # Delete any existing chunks for this entity (re-index)
        from weaviate.classes.query import Filter
        collection.data.delete_many(
            where=Filter.by_property("entity_id").equal(str(entity_id))
        )

        for i, chunk in enumerate(chunks):
            content_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]
            obj_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{entity_id}-{i}")

            properties = {
                "entity_id": str(entity_id),
                "org_id": str(org_id),
                "entity_type": entity_type,
                "title": title,
                "content": chunk,
                "source_integration": source_integration or "",
                "source_url": source_url or "",
                "access_everyone": access_everyone,
                "access_user_ids": access_user_ids or [],
                "chunk_index": i,
                "content_hash": content_hash,
            }

            if embeddings[i] is not None:
                collection.data.insert(
                    uuid=obj_uuid,
                    properties=properties,
                    vector=embeddings[i],
                )
            else:
                collection.data.insert(
                    uuid=obj_uuid,
                    properties=properties,
                )

            vector_ids.append(str(obj_uuid))

        logger.info("Indexed entity %s: %d chunks", entity_id, len(chunks))
    finally:
        client.close()

    return vector_ids


async def delete_entity_vectors(entity_id: uuid.UUID) -> None:
    """Remove all vector chunks for an entity."""
    from weaviate.classes.query import Filter
    client = get_weaviate_client()
    try:
        collection = client.collections.get(COLLECTION_NAME)
        collection.data.delete_many(
            where=Filter.by_property("entity_id").equal(str(entity_id))
        )
    finally:
        client.close()


# ── Search ──


async def hybrid_search(
    query: str,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_types: list[str] | None = None,
    limit: int = 20,
    use_graph: bool = True,
) -> list[dict[str, Any]]:
    """GraphRAG search: vector similarity + keyword matching + graph expansion.

    1. Run hybrid search (Weaviate or SQL fallback)
    2. For top results, expand via entity graph neighbors (1-hop)
    3. Score by relevance + freshness + graph connectivity
    4. Filter by org and permissions

    Falls back to SQL ILIKE search if Weaviate is unavailable.
    Returns ranked results with relevance scores.
    """
    # Step 1: Run base search
    try:
        base_results = await _weaviate_search(query, org_id, user_id, entity_types, limit)
    except Exception:
        logger.warning("Weaviate unavailable, falling back to SQL search", exc_info=True)
        base_results = await _sql_fallback_search(query, org_id, user_id, entity_types, limit)

    if not use_graph or not base_results:
        return _apply_freshness_scoring(base_results)

    # Step 2: Graph expansion — find neighbors of top results
    try:
        expanded = await _graph_expand(base_results, org_id, user_id, entity_types, limit)
        return _apply_freshness_scoring(expanded)
    except Exception:
        logger.debug("Graph expansion failed, returning base results", exc_info=True)
        return _apply_freshness_scoring(base_results)


def _apply_freshness_scoring(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Boost scores for newer content (freshness decay)."""
    import time

    now = time.time()
    for r in results:
        base_score = r.get("score", 0.5)
        # If we have created_at, apply freshness boost
        created_at = r.get("created_at")
        if created_at:
            try:
                from datetime import datetime
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    age_days = (now - dt.timestamp()) / 86400
                else:
                    age_days = 30  # default
                # Freshness multiplier: 1.0 for today, decays to 0.7 at 90 days
                freshness = max(0.7, 1.0 - (age_days / 300))
                r["score"] = base_score * freshness
            except Exception:
                pass

    # Re-sort by adjusted score
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results


async def _graph_expand(
    base_results: list[dict[str, Any]],
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_types: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Expand search results using graph neighbors (GraphRAG).

    For the top 5 results, fetch 1-hop neighbors from the entity graph.
    Neighbors get a boosted score based on their graph proximity.
    """
    from app.db.session import async_session_factory
    from app.services.graph_builder import get_entity_neighbors

    seen_ids = {r["entity_id"] for r in base_results}
    graph_results: list[dict[str, Any]] = []

    async with async_session_factory() as session:
        # Expand top 5 results
        for result in base_results[:5]:
            try:
                entity_id = uuid.UUID(result["entity_id"])
                neighbors = await get_entity_neighbors(
                    entity_id=entity_id,
                    org_id=org_id,
                    db=session,
                    depth=1,
                    limit=10,
                )

                for n in neighbors:
                    nid = n["entity_id"]
                    if nid in seen_ids:
                        continue
                    # Filter by entity types if specified
                    if entity_types and n.get("entity_type") not in entity_types:
                        continue

                    seen_ids.add(nid)
                    # Graph neighbors get a fraction of parent's score
                    parent_score = result.get("score", 0.5)
                    rel_type = n.get("relation_type", "")
                    # "mentions" relations are stronger than "same_label"
                    rel_weight = {
                        "mentions": 0.6,
                        "blocks": 0.7,
                        "comment_on": 0.5,
                        "related_to": 0.4,
                        "same_sprint": 0.3,
                        "same_label": 0.2,
                        "authored_by": 0.3,
                    }.get(rel_type, 0.3)

                    graph_results.append({
                        "entity_id": nid,
                        "entity_type": n.get("entity_type", "document"),
                        "title": n.get("title", ""),
                        "content": n.get("content", ""),
                        "source_url": n.get("source_url"),
                        "source_integration": n.get("source_integration", ""),
                        "score": parent_score * rel_weight,
                        "graph_hop": n.get("hop", 1),
                        "graph_relation": rel_type,
                    })
            except Exception:
                continue

    # Merge base + graph results, sorted by score
    combined = base_results + graph_results
    combined.sort(key=lambda x: x.get("score", 0), reverse=True)
    return combined[:limit]


async def _sql_fallback_search(
    query: str,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_types: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """SQL-based text search fallback when Weaviate is unavailable."""
    from sqlalchemy import select, or_
    from app.db.session import async_session_factory
    from app.db.models import ContextEntity as CE

    # Extract meaningful words (3+ chars) for keyword search
    stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "has", "her",
                  "was", "one", "our", "out", "that", "with", "have", "this", "will", "your",
                  "from", "they", "been", "said", "each", "she", "which", "their", "about",
                  "would", "make", "like", "him", "into", "time", "very", "when", "come",
                  "could", "than", "look", "its", "only", "tell", "what", "who", "how", "where"}
    keywords = [w for w in query.lower().split() if len(w) >= 3 and w not in stop_words]

    if not keywords:
        keywords = [query]

    async with async_session_factory() as session:
        # Build OR conditions: match any keyword in title or content
        conditions = []
        for kw in keywords[:5]:  # limit to 5 keywords
            conditions.append(CE.title.ilike(f"%{kw}%"))
            conditions.append(CE.content.ilike(f"%{kw}%"))

        stmt = (
            select(CE)
            .where(
                CE.org_id == org_id,
                or_(*conditions),
                or_(
                    CE.access_everyone == True,  # noqa: E712
                    CE.access_user_ids.contains([str(user_id)]),
                ),
            )
        )
        if entity_types:
            stmt = stmt.where(CE.entity_type.in_(entity_types))
        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        entities = result.scalars().all()

    return [
        {
            "entity_id": str(e.id),
            "entity_type": e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type),
            "title": e.title,
            "content": (e.content or "")[:500],
            "source_url": e.source_url,
            "source_integration": (e.extra_data or {}).get("source_integration", ""),
            "score": 0.5,
        }
        for e in entities
    ]


async def _weaviate_search(
    query: str,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_types: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Weaviate hybrid search implementation."""
    # Get query embedding
    try:
        query_vector = await get_embedding(query)
    except Exception:
        logger.warning("Query embedding failed, falling back to keyword-only")
        query_vector = None

    client = get_weaviate_client()
    results: list[dict[str, Any]] = []

    try:
        collection = client.collections.get(COLLECTION_NAME)

        from weaviate.classes.query import MetadataQuery, Filter

        # Build filters: org_id + (access_everyone OR user_id in access_user_ids)
        org_filter = Filter.by_property("org_id").equal(str(org_id))

        access_filter = (
            Filter.by_property("access_everyone").equal(True)
            | Filter.by_property("access_user_ids").contains_any([str(user_id)])
        )

        combined_filter = org_filter & access_filter

        if entity_types:
            type_filter = Filter.by_property("entity_type").contains_any(entity_types)
            combined_filter = combined_filter & type_filter

        if query_vector:
            # Hybrid search: combines vector + BM25 keyword
            response = collection.query.hybrid(
                query=query,
                vector=query_vector,
                filters=combined_filter,
                limit=limit,
                alpha=0.7,  # 0.7 = mostly vector, 0.3 keyword
                return_metadata=MetadataQuery(score=True),
            )
        else:
            # Keyword-only fallback
            response = collection.query.bm25(
                query=query,
                filters=combined_filter,
                limit=limit,
                return_metadata=MetadataQuery(score=True),
            )

        # Deduplicate by entity_id (keep highest-scoring chunk per entity)
        seen_entities: dict[str, dict] = {}
        for obj in response.objects:
            entity_id = obj.properties["entity_id"]
            score = obj.metadata.score if obj.metadata.score is not None else 0.0

            if entity_id not in seen_entities or score > seen_entities[entity_id]["score"]:
                seen_entities[entity_id] = {
                    "entity_id": entity_id,
                    "entity_type": obj.properties["entity_type"],
                    "title": obj.properties["title"],
                    "content": obj.properties["content"],
                    "source_url": obj.properties["source_url"],
                    "source_integration": obj.properties["source_integration"],
                    "score": score,
                    "chunk_index": obj.properties["chunk_index"],
                }

        results = sorted(seen_entities.values(), key=lambda x: x["score"], reverse=True)

    finally:
        client.close()

    return results[:limit]
