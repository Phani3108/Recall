"""Skill executor — runtime engine that parses skill step definitions and chains
tool adapter calls to execute reusable workflows.

A Skill's `steps` field is a list of step dicts like:
  [
    {"tool": "jira", "action": "transition_issue", "params": {"issue_key": "{{trigger.issue_key}}", "status": "In Progress"}},
    {"tool": "slack", "action": "post_message", "params": {"channel": "#engineering", "text": "{{trigger.issue_key}} moved to In Progress"}},
  ]

Template variables ({{trigger.*}}, {{steps[n].*}}) are resolved at runtime.
"""

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditAction,
    AuditLog,
    Integration,
    IntegrationProvider,
    Skill,
)
from app.services.tool_adapters import TOOL_REGISTRY
from app.services.tool_adapters.base import ToolResult

logger = logging.getLogger(__name__)

TEMPLATE_RE = re.compile(r"\{\{(.+?)\}\}")


def _resolve_template(template: str, context: dict[str, Any]) -> str:
    """Resolve {{key.sub}} templates against a context dict."""
    def _replace(m: re.Match) -> str:
        path = m.group(1).strip()
        parts = path.replace("[", ".").replace("]", "").split(".")
        val: Any = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, m.group(0))
            elif isinstance(val, list):
                try:
                    val = val[int(p)]
                except (ValueError, IndexError):
                    return m.group(0)
            else:
                return m.group(0)
        return str(val) if val is not None else ""

    return TEMPLATE_RE.sub(_replace, template)


def _resolve_params(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Resolve all template strings in a params dict."""
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str):
            resolved[key] = _resolve_template(value, context)
        elif isinstance(value, list):
            resolved[key] = [
                _resolve_template(v, context) if isinstance(v, str) else v
                for v in value
            ]
        else:
            resolved[key] = value
    return resolved


class SkillExecutionResult:
    """Result of executing a full skill (all steps)."""

    def __init__(self) -> None:
        self.success = True
        self.steps_completed = 0
        self.steps_total = 0
        self.step_results: list[dict[str, Any]] = []
        self.error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "step_results": self.step_results,
            "error": self.error,
        }


async def execute_skill(
    skill: Skill,
    trigger_data: dict[str, Any],
    db: AsyncSession,
) -> SkillExecutionResult:
    """Execute all steps of a skill sequentially.

    Args:
        skill: The skill to execute.
        trigger_data: Data from the trigger event (e.g., issue_key, pr_number).
        db: Database session.

    Returns:
        SkillExecutionResult with per-step outcomes.
    """
    result = SkillExecutionResult()
    steps: list[dict[str, Any]] = skill.steps or []
    result.steps_total = len(steps)

    # Build execution context
    context: dict[str, Any] = {
        "trigger": trigger_data,
        "skill": {"name": skill.name, "id": str(skill.id)},
        "steps": [],
    }

    for i, step in enumerate(steps):
        tool_name = step.get("tool", "")
        action_name = step.get("action", "")
        raw_params = step.get("params", {})

        # Resolve template variables
        params = _resolve_params(raw_params, context)

        # Get tool adapter
        tool_cls = TOOL_REGISTRY.get(tool_name)
        if not tool_cls:
            step_result = {"step": i, "tool": tool_name, "action": action_name,
                           "success": False, "message": f"No adapter for '{tool_name}'"}
            result.step_results.append(step_result)
            context["steps"].append(step_result)
            result.success = False
            result.error = f"Step {i}: no adapter for '{tool_name}'"
            break

        tool = tool_cls()

        # Look up integration
        try:
            provider = IntegrationProvider(tool_name)
        except ValueError:
            step_result = {"step": i, "tool": tool_name, "action": action_name,
                           "success": False, "message": f"Unknown provider: {tool_name}"}
            result.step_results.append(step_result)
            context["steps"].append(step_result)
            result.success = False
            result.error = f"Step {i}: unknown provider '{tool_name}'"
            break

        int_result = await db.execute(
            select(Integration).where(
                Integration.org_id == skill.org_id,
                Integration.provider == provider,
            )
        )
        integration = int_result.scalar_one_or_none()

        if not integration or not integration.config:
            step_result = {"step": i, "tool": tool_name, "action": action_name,
                           "success": False, "message": f"No connected {tool_name} integration"}
            result.step_results.append(step_result)
            context["steps"].append(step_result)
            result.success = False
            result.error = f"Step {i}: no connected {tool_name} integration"
            break

        # Execute step
        try:
            tool_result: ToolResult = await tool.execute(action_name, params, integration.config)
            step_result = {
                "step": i,
                "tool": tool_name,
                "action": action_name,
                "success": tool_result.success,
                "message": tool_result.message,
                "data": tool_result.data,
                "url": tool_result.url,
            }
        except Exception as e:
            logger.error("Skill step %d failed: %s", i, e, exc_info=True)
            step_result = {"step": i, "tool": tool_name, "action": action_name,
                           "success": False, "message": str(e)}

        result.step_results.append(step_result)
        context["steps"].append(step_result)

        if step_result["success"]:
            result.steps_completed += 1
        else:
            # Stop on first failure (can be made configurable)
            if step.get("continue_on_error", False):
                continue
            result.success = False
            result.error = f"Step {i} ({tool_name}.{action_name}) failed: {step_result['message']}"
            break

    # Update execution count
    skill.execution_count += 1

    # Audit log
    db.add(AuditLog(
        org_id=skill.org_id,
        user_id=None,
        action=AuditAction.SKILL_EXECUTION,
        resource_type="skill",
        resource_id=skill.id,
        detail={
            "skill_name": skill.name,
            "steps_completed": result.steps_completed,
            "steps_total": result.steps_total,
            "success": result.success,
            "trigger_data": trigger_data,
        },
    ))
    await db.flush()

    return result


# ── Built-in skill templates ──

BUILTIN_SKILLS: list[dict[str, Any]] = [
    {
        "name": "Standup Summary",
        "description": "Posts a daily standup summary to Slack with recent activity from Jira and GitHub.",
        "trigger": {"type": "scheduled", "cron": "0 9 * * 1-5"},
        "steps": [
            {"tool": "slack", "action": "post_message", "params": {
                "channel": "#standup",
                "text": "🌅 *Daily Standup Summary*\n\nHere's what happened in the last 24 hours across your tools. Check Flow for details.",
            }},
        ],
    },
    {
        "name": "PR Review Reminder",
        "description": "Sends a Slack reminder when a PR has been open for more than 24 hours without a review.",
        "trigger": {"type": "on_pattern", "pattern": "stale_pr"},
        "steps": [
            {"tool": "slack", "action": "post_message", "params": {
                "channel": "#engineering",
                "text": "👀 *Review Needed*: PR {{trigger.pr_title}} has been open for {{trigger.age_days}} days without a review.",
            }},
        ],
    },
    {
        "name": "Sprint Report",
        "description": "Generates a summary of completed vs remaining sprint items and posts to Slack.",
        "trigger": {"type": "scheduled", "cron": "0 17 * * 5"},
        "steps": [
            {"tool": "slack", "action": "post_message", "params": {
                "channel": "#engineering",
                "text": "📊 *Sprint Report*\n\nCompleted items this sprint are posted above. Review the Flow board for remaining work.",
            }},
        ],
    },
    {
        "name": "Knowledge Digest",
        "description": "Posts a weekly digest of new documents and decisions to a Slack channel.",
        "trigger": {"type": "scheduled", "cron": "0 10 * * 1"},
        "steps": [
            {"tool": "slack", "action": "post_message", "params": {
                "channel": "#knowledge",
                "text": "📚 *Weekly Knowledge Digest*\n\nNew documents and decisions from the past week. Check the Knowledge Graph for the full picture.",
            }},
        ],
    },
    {
        "name": "Onboarding Checklist",
        "description": "Creates a Jira onboarding task with standard checklist items for a new team member.",
        "trigger": {"type": "manual"},
        "steps": [
            {"tool": "jira", "action": "create_issue", "params": {
                "project_key": "{{trigger.project_key}}",
                "summary": "Onboarding: {{trigger.new_member_name}}",
            }},
        ],
    },
]
