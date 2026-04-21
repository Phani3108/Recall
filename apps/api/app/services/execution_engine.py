"""Execution engine — routes approved delegations to the appropriate tool adapter.

This is the bridge between the Pilot (delegation proposals) and the Tool Adapters
(actual API calls). When a delegation is approved, the engine:

1. Parses the delegation action to determine tool + action + params
2. Looks up the integration config for the target tool
3. Invokes the tool adapter
4. Records the execution result on the delegation
5. Logs the execution in the audit trail
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditAction,
    AuditLog,
    Delegation,
    DelegationStatus,
    Integration,
    IntegrationProvider,
)
from app.services.tool_adapters import TOOL_REGISTRY
from app.services.tool_adapters.base import ToolResult

logger = logging.getLogger(__name__)


# ── Action parsing ──

# Maps common action phrases to (tool, action, param_extractor) tuples
ACTION_PATTERNS: list[tuple[str, str, str, list[str]]] = [
    # Jira
    (r"move (\S+) to (.+)", "jira", "transition_issue", ["issue_key", "status"]),
    (r"transition (\S+) to (.+)", "jira", "transition_issue", ["issue_key", "status"]),
    (r"comment on (\S+)[:\s]+(.+)", "jira", "comment_on_issue", ["issue_key", "body"]),
    (r"assign (\S+) to (.+)", "jira", "assign_issue", ["issue_key", "account_id"]),
    (r"create jira (?:issue|ticket) in (\S+)[:\s]+(.+)", "jira", "create_issue", ["project_key", "summary"]),
    (r"add label (\S+) to (\S+)", "jira", "add_label", ["_labels", "issue_key"]),
    # GitHub
    (r"create issue in (\S+)[:\s]+(.+)", "github", "create_issue", ["repo", "title"]),
    (r"comment on #(\d+) in (\S+)[:\s]+(.+)", "github", "comment_on_issue", ["issue_number", "repo", "body"]),
    (r"close #(\d+) in (\S+)", "github", "close_issue", ["issue_number", "repo"]),
    (r"request review from (.+) on PR #(\d+) in (\S+)", "github", "request_review", ["_reviewers", "pr_number", "repo"]),
    # Slack
    (r"post to (#\S+)[:\s]+(.+)", "slack", "post_message", ["channel", "text"]),
    (r"send message to (#\S+)[:\s]+(.+)", "slack", "post_message", ["channel", "text"]),
    (r"post (?:standup |sprint )?summary to (#\S+)", "slack", "post_message", ["channel"]),
    # Confluence
    (r"create page in space (\S+)[:\s]+(.+)", "confluence", "create_page", ["space_id", "title"]),
    (r"comment on page (\S+)[:\s]+(.+)", "confluence", "add_comment", ["page_id", "body"]),
]


def parse_delegation_action(action_text: str, tool_hint: str | None = None) -> dict[str, Any] | None:
    """Parse a natural-language delegation action into tool/action/params.

    Returns dict with keys: tool, action, params — or None if no pattern matches.
    """
    action_lower = action_text.lower().strip()

    for pattern, tool, action, param_names in ACTION_PATTERNS:
        if tool_hint and tool != tool_hint:
            continue
        m = re.search(pattern, action_lower, re.IGNORECASE)
        if m:
            params = {}
            for i, name in enumerate(param_names):
                value = m.group(i + 1).strip()
                if name == "_labels":
                    params["labels"] = [v.strip() for v in value.split(",")]
                elif name == "_reviewers":
                    params["reviewers"] = [v.strip() for v in value.split(",")]
                elif name == "issue_number" or name == "pr_number":
                    params[name] = int(value)
                else:
                    params[name] = value
            return {"tool": tool, "action": action, "params": params}

    return None


def normalize_execution_payload(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return ``{tool, action, params}`` if the payload is valid for a registered adapter."""
    if not raw or not isinstance(raw, dict):
        return None
    tool = raw.get("tool")
    action = raw.get("action")
    params = raw.get("params")
    if not isinstance(tool, str) or not isinstance(action, str):
        return None
    if not isinstance(params, dict):
        params = {}
    tool_cls = TOOL_REGISTRY.get(tool)
    if not tool_cls:
        return None
    adapter = tool_cls()
    if action not in adapter.supported_actions:
        return None
    return {"tool": tool, "action": action, "params": params}


def build_execution_payload_best_effort(action_text: str, tool_hint: str | None) -> dict[str, Any] | None:
    """Best-effort structured payload from natural language (regex templates only)."""
    parsed = parse_delegation_action(action_text, tool_hint=tool_hint)
    if not parsed:
        return None
    return normalize_execution_payload(parsed)


# ── Execution ──


async def execute_delegation(
    delegation: Delegation,
    db: AsyncSession,
) -> ToolResult:
    """Execute an approved delegation by routing it to the appropriate tool adapter.

    1. Prefer ``delegation.execution_payload`` when valid
    2. Else parse natural-language ``action`` (regex + fallbacks)
    3. Look up integration config and invoke the tool adapter
    4. Record result
    """
    parsed = normalize_execution_payload(
        delegation.execution_payload
        if isinstance(delegation.execution_payload, dict)
        else None
    )
    if not parsed:
        parsed = parse_delegation_action(delegation.action, tool_hint=delegation.tool)
    if not parsed:
        parsed = {
            "tool": delegation.tool,
            "action": _guess_action(delegation.tool, delegation.action),
            "params": {"text": delegation.action},
        }

    tool_name = parsed["tool"]
    action_name = parsed["action"]
    params = parsed["params"]

    # Get tool adapter
    tool_cls = TOOL_REGISTRY.get(tool_name)
    if not tool_cls:
        result = ToolResult(
            success=False,
            action=action_name,
            message=f"No tool adapter found for '{tool_name}'",
        )
        await _record_result(delegation, result, db)
        return result

    tool = tool_cls()

    # Look up integration config for this tool + org
    try:
        provider = IntegrationProvider(tool_name)
    except ValueError:
        result = ToolResult(
            success=False,
            action=action_name,
            message=f"Unknown provider: {tool_name}",
        )
        await _record_result(delegation, result, db)
        return result

    integration_result = await db.execute(
        select(Integration).where(
            Integration.org_id == delegation.org_id,
            Integration.provider == provider,
        )
    )
    integration = integration_result.scalar_one_or_none()

    if not integration or not integration.config:
        result = ToolResult(
            success=False,
            action=action_name,
            message=f"No connected {tool_name} integration found. Connect it in Integrations first.",
        )
        await _record_result(delegation, result, db)
        return result

    # Execute
    try:
        result = await tool.execute(action_name, params, integration.config)
    except Exception as e:
        logger.error("Tool execution failed: %s", e, exc_info=True)
        result = ToolResult(
            success=False,
            action=action_name,
            message=f"Execution failed: {type(e).__name__}: {e}",
        )

    await _record_result(delegation, result, db)
    return result


def _guess_action(tool: str, action_text: str) -> str:
    """Guess the most likely action for a tool based on action text keywords."""
    text = action_text.lower()

    guesses = {
        "jira": [
            ("transition", "transition_issue"),
            ("move", "transition_issue"),
            ("comment", "comment_on_issue"),
            ("assign", "assign_issue"),
            ("create", "create_issue"),
            ("label", "add_label"),
            ("priority", "update_priority"),
        ],
        "github": [
            ("comment", "comment_on_issue"),
            ("close", "close_issue"),
            ("create issue", "create_issue"),
            ("create pr", "create_pull_request"),
            ("review", "request_review"),
            ("label", "add_label"),
        ],
        "slack": [
            ("post", "post_message"),
            ("send", "post_message"),
            ("reply", "reply_to_thread"),
            ("topic", "set_topic"),
        ],
        "confluence": [
            ("create page", "create_page"),
            ("update", "update_page"),
            ("comment", "add_comment"),
        ],
    }

    for keyword, action in guesses.get(tool, []):
        if keyword in text:
            return action

    # Default action per tool
    defaults = {
        "jira": "comment_on_issue",
        "github": "comment_on_issue",
        "slack": "post_message",
        "confluence": "add_comment",
    }
    return defaults.get(tool, "unknown")


async def _record_result(
    delegation: Delegation,
    result: ToolResult,
    db: AsyncSession,
) -> None:
    """Record execution result on the delegation and audit log."""
    delegation.status = DelegationStatus.EXECUTED if result.success else DelegationStatus.APPROVED
    delegation.execution_result = {
        "success": result.success,
        "action": result.action,
        "message": result.message,
        "data": result.data,
        "url": result.url,
        "executed_at": datetime.now(UTC).isoformat(),
    }

    db.add(AuditLog(
        org_id=delegation.org_id,
        user_id=delegation.resolved_by_user_id,
        action=AuditAction.DELEGATION_EXECUTED,
        resource_type="delegation",
        resource_id=delegation.id,
        detail={
            "tool": delegation.tool,
            "action_text": delegation.action,
            "result": result.message,
            "success": result.success,
        },
    ))
    await db.flush()
