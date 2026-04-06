"""Agent/chat routes — Ask chat interface with RAG pipeline.

Uses Weaviate hybrid search for context retrieval and LiteLLM for LLM calls.
Falls back to a basic response if services are unavailable.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, async_session_factory
from app.db.models import Conversation, Message, AuditLog, AuditAction
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.llm_service import chat, chat_stream, ConversationMessage

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_session():
    """Get a fresh async session for use after streaming completes."""
    return async_session_factory()


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.org_id == ctx.org_id, Conversation.user_id == ctx.user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    conversations = result.scalars().all()
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            user_id=c.user_id,
            is_shared=c.is_shared,
            created_at=c.created_at,
        )
        for c in conversations
    ]


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    req: ConversationCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    conversation = Conversation(
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        title=req.title,
    )
    db.add(conversation)
    await db.flush()
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        user_id=conversation.user_id,
        is_shared=conversation.is_shared,
        created_at=conversation.created_at,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    # Verify conversation belongs to user/org
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.org_id == ctx.org_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != ctx.user_id and not conversation.is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=m.sources,
            tool_calls=m.tool_calls,
            tokens_used=m.tokens_used,
            model=m.model,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    conversation_id: uuid.UUID,
    req: MessageCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Send a message and get an AI response.

    Phase 0: stores the message, returns a placeholder response.
    Phase 1: RAG pipeline → context retrieval → LLM call → response with sources.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.org_id == ctx.org_id,
            Conversation.user_id == ctx.user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Store user message
    user_msg = Message(
        org_id=ctx.org_id,
        conversation_id=conversation_id,
        role="user",
        content=req.content,
    )
    db.add(user_msg)
    await db.flush()

    # Load conversation history for context
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(40)
    )
    history = [
        ConversationMessage(role=m.role, content=m.content)
        for m in history_result.scalars().all()
        if m.id != user_msg.id  # exclude the just-added user msg (it's passed separately)
    ]

    # Call RAG pipeline
    chat_response = await chat(
        user_query=req.content,
        conversation_history=history,
        org_id=ctx.org_id,
        user_id=ctx.user_id,
    )

    # Store assistant response
    sources_data = [
        {
            "entity_id": s.entity_id,
            "title": s.title,
            "source_url": s.source_url,
            "source_integration": s.source_integration,
            "relevance_score": s.relevance_score,
        }
        for s in chat_response.sources
    ]

    assistant_msg = Message(
        org_id=ctx.org_id,
        conversation_id=conversation_id,
        role="assistant",
        content=chat_response.content,
        sources=sources_data,
        tool_calls=[],
        tokens_used=chat_response.tokens_total,
        model=chat_response.model,
    )
    db.add(assistant_msg)

    # Log to audit trail
    audit = AuditLog(
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        action=AuditAction.AI_QUERY,
        resource_type="conversation",
        resource_id=conversation_id,
        detail={
            "model": chat_response.model,
            "tokens": chat_response.tokens_total,
            "cost_usd": chat_response.cost_usd,
            "latency_ms": chat_response.latency_ms,
            "sources_count": len(chat_response.sources),
        },
        tokens_consumed=chat_response.tokens_total,
        cost_usd=chat_response.cost_usd,
        model_used=chat_response.model,
    )
    db.add(audit)

    # Auto-title conversation if it's the first message
    if conversation.title is None:
        conversation.title = req.content[:80].strip()

    await db.flush()

    return MessageResponse(
        id=assistant_msg.id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        sources=assistant_msg.sources,
        tool_calls=assistant_msg.tool_calls,
        tokens_used=assistant_msg.tokens_used,
        model=assistant_msg.model,
        created_at=assistant_msg.created_at,
    )


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: uuid.UUID,
    req: MessageCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and stream the AI response via SSE."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.org_id == ctx.org_id,
            Conversation.user_id == ctx.user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Store user message
    user_msg = Message(
        org_id=ctx.org_id,
        conversation_id=conversation_id,
        role="user",
        content=req.content,
    )
    db.add(user_msg)

    # Auto-title
    if conversation.title is None:
        conversation.title = req.content[:80].strip()

    await db.flush()
    await db.commit()

    # Load history
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(40)
    )
    history = [
        ConversationMessage(role=m.role, content=m.content)
        for m in history_result.scalars().all()
        if m.id != user_msg.id
    ]

    async def event_generator():
        full_content = ""
        model_used = "mock-mode"
        tokens_total = 0

        async for chunk in chat_stream(
            user_query=req.content,
            conversation_history=history,
            org_id=ctx.org_id,
            user_id=ctx.user_id,
        ):
            yield chunk

            # Capture content from delta events for DB persistence
            if chunk.startswith("event: delta\ndata: "):
                import json
                try:
                    text = json.loads(chunk.split("data: ", 1)[1].strip())
                    full_content += text
                except Exception:
                    pass
            elif chunk.startswith("event: done\ndata: "):
                import json
                try:
                    meta = json.loads(chunk.split("data: ", 1)[1].strip())
                    model_used = meta.get("model", "mock-mode")
                    tokens_total = meta.get("tokens_total", 0)
                except Exception:
                    pass

        # Persist assistant message after streaming completes
        async with (await _get_session()) as save_db:
            assistant_msg = Message(
                org_id=ctx.org_id,
                conversation_id=conversation_id,
                role="assistant",
                content=full_content,
                sources=[],
                tool_calls=[],
                tokens_used=tokens_total,
                model=model_used,
            )
            save_db.add(assistant_msg)
            save_db.add(AuditLog(
                org_id=ctx.org_id,
                user_id=ctx.user_id,
                action=AuditAction.AI_QUERY,
                resource_type="conversation",
                resource_id=conversation_id,
                detail={"model": model_used, "tokens": tokens_total, "streamed": True},
                tokens_consumed=tokens_total,
                cost_usd=0.0,
                model_used=model_used,
            ))
            await save_db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
