"""Optional NL → structured Pilot execution payload (regex first, then LLM JSON)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.execution_engine import (
    build_execution_payload_best_effort,
    normalize_execution_payload,
)
from app.services.llm_service import _call_llm, _is_mock_mode
from app.services.tool_adapters import TOOL_REGISTRY

logger = logging.getLogger(__name__)


def _adapter_catalog_text() -> str:
    lines: list[str] = []
    for name, cls in TOOL_REGISTRY.items():
        inst = cls()
        lines.append(f"- {name}: {', '.join(inst.supported_actions)}")
    return "\n".join(lines)


async def suggest_execution_payload(
    action: str,
    tool_hint: str | None,
) -> tuple[dict[str, Any] | None, str]:
    """Return ``(execution_payload, source)`` where source is ``regex``, ``llm``, or ``none``."""
    action = action.strip()
    if not action:
        return None, "none"

    via_regex = build_execution_payload_best_effort(action, tool_hint)
    if via_regex:
        return via_regex, "regex"

    if _is_mock_mode():
        return None, "none"

    catalog = _adapter_catalog_text()
    hint = tool_hint or "infer from the instruction"
    messages = [
        {
            "role": "system",
            "content": (
                "You map a user's instruction to a single tool call. "
                "Reply with JSON only: {\"tool\": string, \"action\": string, \"params\": object}.\n"
                "If you cannot map safely, use empty strings for tool and action and {} for params.\n\n"
                f"Supported tools and actions:\n{catalog}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Preferred tool hint: {hint}\n\nInstruction:\n{action}"
            ),
        },
    ]

    try:
        data = await _call_llm(
            messages,
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw_content = data["choices"][0]["message"]["content"]
        obj = json.loads(raw_content)
        normalized = normalize_execution_payload(obj)
        if normalized:
            return normalized, "llm"
    except Exception as e:
        logger.warning("LLM delegation suggest failed: %s", e, exc_info=True)

    return None, "none"
