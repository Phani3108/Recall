"""LLM service — RAG pipeline powering Ask chat.

Handles: context retrieval → prompt augmentation → LLM call → source attribution → audit logging.
When no API key is configured, returns realistic mock responses using available context.
"""

import uuid
import json
import logging
import time
import random
import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator

import httpx

from app.config import settings
from app.services.context_engine import hybrid_search

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are Ask, the AI assistant for Recall — an AI-native Work OS. 
You have access to the user's organization context from connected tools (Slack, GitHub, Jira, Notion, Google Workspace, etc.).

Rules:
1. Answer using the provided context. If the context doesn't contain enough information, say so honestly.
2. Always cite your sources using [Source: title](url) format when referencing specific information.
3. Be concise but thorough. Prefer structured responses (bullets, headers) for complex answers.
4. If asked to perform an action (create ticket, send message, etc.), explain what you would do and confirm before executing.
5. Never fabricate information. If you're unsure, say "I don't have enough context to answer that confidently."
6. Respect data boundaries — only reference information from the provided context.
"""


def _is_mock_mode(api_key: str | None = None) -> bool:
    """Check if we should use mock mode (no real LLM API key configured)."""
    if api_key:
        return False
    return not settings.openai_api_key and not settings.anthropic_api_key


# ── Mock response generation ──

_MOCK_TEMPLATES = [
    {
        "keywords": ["who", "team", "person", "contact", "owner", "responsible"],
        "response": """Based on the available context, here's what I found:

**{source_title}** is relevant to your question.

{context_summary}

**Key people involved:**
- The document was last updated recently and appears to be actively maintained
- Check the linked source for the most current information

[Source: {source_title}]({source_url})""",
    },
    {
        "keywords": ["how", "process", "steps", "guide", "setup", "configure"],
        "response": """Here's what I found in your organization's knowledge base:

**From: {source_title}**

{context_summary}

**Recommended next steps:**
1. Review the linked document for full details
2. Check with the team if you need clarification
3. The process may have been updated since the document was last modified

[Source: {source_title}]({source_url})""",
    },
    {
        "keywords": ["status", "update", "progress", "blockers", "sprint"],
        "response": """Here's the latest context I found:

**{source_title}**

{context_summary}

**Summary:**
- This information comes from your connected tools
- For real-time status, check the linked source directly

[Source: {source_title}]({source_url})""",
    },
    {
        "keywords": [],  # default fallback
        "response": """I found some relevant context for your question:

**{source_title}**

{context_summary}

This information was retrieved from your organization's connected tools. Let me know if you'd like me to dig deeper into any specific aspect.

[Source: {source_title}]({source_url})""",
    },
]


def _generate_mock_response(
    query: str, search_results: list[dict]
) -> tuple[str, list["ChatSource"]]:
    """Generate a realistic mock response using available context."""
    query_lower = query.lower()

    # Pick the best template based on keywords
    template = _MOCK_TEMPLATES[-1]  # default
    for t in _MOCK_TEMPLATES[:-1]:
        if any(kw in query_lower for kw in t["keywords"]):
            template = t
            break

    if search_results:
        top = search_results[0]
        content = top.get("content", "")
        # Use first ~200 chars of content as summary
        context_summary = content[:200].strip()
        if len(content) > 200:
            context_summary += "..."

        response_text = template["response"].format(
            source_title=top.get("title", "Document"),
            source_url=top.get("source_url", "#"),
            context_summary=context_summary,
        )

        sources = [
            ChatSource(
                entity_id=r.get("entity_id", ""),
                title=r.get("title", ""),
                source_url=r.get("source_url", ""),
                source_integration=r.get("source_integration", ""),
                relevance_score=r.get("score", 0.0),
            )
            for r in search_results[:3]
        ]
    else:
        response_text = (
            f"I searched across your connected tools but couldn't find specific context "
            f'for "{query}". This could mean:\n\n'
            "1. The relevant data hasn't been synced yet\n"
            "2. The information exists in a tool that isn't connected\n"
            "3. Try rephrasing your question with different keywords\n\n"
            "**Tip:** Connect more integrations in Settings → Integrations to expand my knowledge."
        )
        sources = []

    return response_text, sources


@dataclass
class ChatSource:
    entity_id: str
    title: str
    source_url: str
    source_integration: str
    relevance_score: float


@dataclass
class ChatResponse:
    content: str
    sources: list[ChatSource]
    model: str
    tokens_prompt: int
    tokens_completion: int
    tokens_total: int
    latency_ms: int
    cost_usd: float


@dataclass
class ConversationMessage:
    role: str  # user, assistant, system
    content: str


async def _call_llm(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    api_key: str | None = None,
) -> dict:
    """Call LLM — direct OpenAI if api_key provided, otherwise LiteLLM proxy."""
    key = api_key or settings.openai_api_key
    if key:
        # Direct OpenAI API call
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            )
            resp.raise_for_status()
            return resp.json()

    # Fallback: LiteLLM proxy
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.litellm_proxy_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()


def _build_context_block(search_results: list[dict]) -> str:
    """Format search results into a context block for the LLM prompt."""
    if not search_results:
        return "No relevant context found in connected tools."

    blocks = []
    for i, result in enumerate(search_results, 1):
        source_label = result.get("source_integration", "unknown")
        url = result.get("source_url", "")
        title = result.get("title", "Untitled")
        content = result.get("content", "")

        block = f"[Source {i}: {title}]({url})\nFrom: {source_label}\n{content}"
        blocks.append(block)

    return "\n\n---\n\n".join(blocks)


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Rough cost estimation per model. Updated as needed."""
    rates = {
        "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "claude-sonnet": (3.00 / 1_000_000, 15.00 / 1_000_000),
        "claude-haiku": (0.25 / 1_000_000, 1.25 / 1_000_000),
    }
    input_rate, output_rate = rates.get(model, (0.50 / 1_000_000, 1.50 / 1_000_000))
    return round(prompt_tokens * input_rate + completion_tokens * output_rate, 6)


async def chat(
    user_query: str,
    conversation_history: list[ConversationMessage],
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> ChatResponse:
    """Full RAG pipeline: search context → augment prompt → call LLM → return attributed response.

    1. Search the unified context graph for relevant entities
    2. Build an augmented prompt with retrieved context
    3. Call LLM via LiteLLM proxy (or mock mode if no API key)
    4. Extract and attribute sources
    5. Track token usage and cost
    """
    start_time = time.monotonic()

    # Step 1: Retrieve relevant context
    search_results = []
    try:
        search_results = await hybrid_search(
            query=user_query,
            org_id=org_id,
            user_id=user_id,
            limit=8,
        )
    except Exception:
        logger.warning("Context search failed, proceeding without context", exc_info=True)

    # Mock mode: return realistic response without calling LLM
    if _is_mock_mode(api_key):
        logger.info("Mock mode active (no API key configured)")
        content, sources = _generate_mock_response(user_query, search_results)
        latency_ms = int((time.monotonic() - start_time) * 1000)
        mock_prompt_tokens = len(user_query.split()) * 2
        mock_completion_tokens = len(content.split()) * 2
        return ChatResponse(
            content=content,
            sources=sources,
            model="mock-mode",
            tokens_prompt=mock_prompt_tokens,
            tokens_completion=mock_completion_tokens,
            tokens_total=mock_prompt_tokens + mock_completion_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,
        )

    # Step 2: Build augmented prompt
    context_block = _build_context_block(search_results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"## Retrieved Context from Connected Tools\n\n{context_block}",
        },
    ]

    # Add conversation history (last 20 messages for context window management)
    for msg in conversation_history[-20:]:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_query})

    # Step 3: Call LLM
    try:
        llm_response = await _call_llm(messages, model=model, api_key=api_key)
    except httpx.HTTPStatusError as e:
        logger.error("LLM call failed: %s", e.response.text)
        return ChatResponse(
            content="I'm having trouble connecting to the AI service right now. Please try again in a moment.",
            sources=[],
            model=model,
            tokens_prompt=0,
            tokens_completion=0,
            tokens_total=0,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            cost_usd=0.0,
        )
    except Exception:
        logger.error("LLM call failed", exc_info=True)
        return ChatResponse(
            content="Something went wrong while processing your request. Please try again.",
            sources=[],
            model=model,
            tokens_prompt=0,
            tokens_completion=0,
            tokens_total=0,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            cost_usd=0.0,
        )

    # Step 4: Extract response and usage
    choice = llm_response["choices"][0]
    content = choice["message"]["content"]
    usage = llm_response.get("usage", {})
    tokens_prompt = usage.get("prompt_tokens", 0)
    tokens_completion = usage.get("completion_tokens", 0)
    tokens_total = usage.get("total_tokens", 0)

    # Step 5: Build source attributions
    sources = [
        ChatSource(
            entity_id=r["entity_id"],
            title=r["title"],
            source_url=r.get("source_url", ""),
            source_integration=r.get("source_integration", ""),
            relevance_score=r.get("score", 0.0),
        )
        for r in search_results
        if r.get("title", "").lower() in content.lower()  # Only include actually-referenced sources
    ]

    # If LLM cited sources but our heuristic missed them, include all top results
    if not sources and search_results:
        sources = [
            ChatSource(
                entity_id=r["entity_id"],
                title=r["title"],
                source_url=r.get("source_url", ""),
                source_integration=r.get("source_integration", ""),
                relevance_score=r.get("score", 0.0),
            )
            for r in search_results[:3]
        ]

    latency_ms = int((time.monotonic() - start_time) * 1000)

    return ChatResponse(
        content=content,
        sources=sources,
        model=llm_response.get("model", model),
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        tokens_total=tokens_total,
        latency_ms=latency_ms,
        cost_usd=_estimate_cost(model, tokens_prompt, tokens_completion),
    )


async def chat_stream(
    user_query: str,
    conversation_history: list[ConversationMessage],
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    """Streaming version of chat — yields SSE-formatted chunks.

    Event types:
        - sources: JSON array of source attributions (sent first)
        - delta: text chunk of the response
        - done: final metadata (model, tokens, cost)
        - error: error message
    """
    start_time = time.monotonic()

    # Step 1: Retrieve context
    search_results = []
    try:
        search_results = await hybrid_search(
            query=user_query, org_id=org_id, user_id=user_id, limit=8,
        )
    except Exception:
        logger.warning("Context search failed in stream", exc_info=True)

    # Send sources first
    sources = [
        {
            "entity_id": r.get("entity_id", ""),
            "title": r.get("title", ""),
            "source_url": r.get("source_url", ""),
            "source_integration": r.get("source_integration", ""),
            "relevance_score": r.get("score", 0.0),
        }
        for r in search_results[:3]
    ]
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    # Mock mode: simulate streaming by yielding word-by-word
    if _is_mock_mode(api_key):
        content, _ = _generate_mock_response(user_query, search_results)
        words = content.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            yield f"event: delta\ndata: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(random.uniform(0.02, 0.06))

        latency_ms = int((time.monotonic() - start_time) * 1000)
        yield f"event: done\ndata: {json.dumps({'model': 'mock-mode', 'tokens_total': len(words) * 2, 'latency_ms': latency_ms, 'cost_usd': 0.0})}\n\n"
        return

    # Real LLM: stream from OpenAI (direct or via LiteLLM proxy)
    context_block = _build_context_block(search_results)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"## Retrieved Context from Connected Tools\n\n{context_block}"},
    ]
    for msg in conversation_history[-20:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_query})

    key = api_key or settings.openai_api_key
    if key:
        base_url = "https://api.openai.com/v1"
        auth_header = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    else:
        base_url = settings.litellm_proxy_url
        auth_header = {"Authorization": f"Bearer {settings.litellm_master_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=auth_header,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                full_content = ""
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            full_content += text
                            yield f"event: delta\ndata: {json.dumps(text)}\n\n"
                    except json.JSONDecodeError:
                        continue

        latency_ms = int((time.monotonic() - start_time) * 1000)
        tokens_est = len(full_content.split()) * 2
        yield f"event: done\ndata: {json.dumps({'model': model, 'tokens_total': tokens_est, 'latency_ms': latency_ms, 'cost_usd': 0.0})}\n\n"
    except Exception as exc:
        logger.error("Streaming LLM call failed", exc_info=True)
        yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
