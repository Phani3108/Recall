"""Jira tool adapter — create issues, transition tickets, add comments via Jira API."""

import base64
import logging
from typing import Any

import httpx

from app.services.tool_adapters.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class JiraTool(BaseTool):
    name = "jira"
    supported_actions = [
        "create_issue",
        "transition_issue",
        "comment_on_issue",
        "assign_issue",
        "add_label",
        "update_priority",
    ]

    def _get_headers(self, config: dict) -> tuple[dict, str]:
        email = config["email"]
        token = config["token"]
        domain = config["domain"].replace("https://", "").replace("http://", "").rstrip("/")
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}", "Accept": "application/json", "Content-Type": "application/json"}
        return headers, domain

    async def execute(self, action: str, params: dict[str, Any], config: dict) -> ToolResult:
        self._validate_action(action)
        headers, domain = self._get_headers(config)

        dispatch = {
            "create_issue": self._create_issue,
            "transition_issue": self._transition_issue,
            "comment_on_issue": self._comment_on_issue,
            "assign_issue": self._assign_issue,
            "add_label": self._add_label,
            "update_priority": self._update_priority,
        }
        return await dispatch[action](params, headers, domain)

    async def _create_issue(self, params: dict, headers: dict, domain: str) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://{domain}/rest/api/3/issue",
                headers=headers,
                json={
                    "fields": {
                        "project": {"key": params["project_key"]},
                        "summary": params["summary"],
                        "description": {
                            "type": "doc", "version": 1,
                            "content": [{"type": "paragraph", "content": [
                                {"type": "text", "text": params.get("description", "")}
                            ]}],
                        },
                        "issuetype": {"name": params.get("issue_type", "Task")},
                    }
                },
            )
            resp.raise_for_status()
            issue = resp.json()
            return ToolResult(
                success=True,
                action="create_issue",
                message=f"Created {issue['key']}: {params['summary']}",
                data={"key": issue["key"], "id": issue["id"]},
                url=f"https://{domain}/browse/{issue['key']}",
            )

    async def _transition_issue(self, params: dict, headers: dict, domain: str) -> ToolResult:
        issue_key = params["issue_key"]
        target_status = params["status"].lower()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get available transitions
            resp = await client.get(
                f"https://{domain}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
            )
            resp.raise_for_status()
            transitions = resp.json().get("transitions", [])

            # Find matching transition
            transition_id = None
            for t in transitions:
                if t["name"].lower() == target_status or t["to"]["name"].lower() == target_status:
                    transition_id = t["id"]
                    break

            if not transition_id:
                available = [t["name"] for t in transitions]
                return ToolResult(
                    success=False,
                    action="transition_issue",
                    message=f"Cannot transition {issue_key} to '{params['status']}'. Available: {available}",
                )

            resp = await client.post(
                f"https://{domain}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
                json={"transition": {"id": transition_id}},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="transition_issue",
                message=f"Transitioned {issue_key} to {params['status']}",
                url=f"https://{domain}/browse/{issue_key}",
            )

    async def _comment_on_issue(self, params: dict, headers: dict, domain: str) -> ToolResult:
        issue_key = params["issue_key"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://{domain}/rest/api/3/issue/{issue_key}/comment",
                headers=headers,
                json={
                    "body": {
                        "type": "doc", "version": 1,
                        "content": [{"type": "paragraph", "content": [
                            {"type": "text", "text": params["body"]}
                        ]}],
                    }
                },
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="comment_on_issue",
                message=f"Commented on {issue_key}",
                url=f"https://{domain}/browse/{issue_key}",
            )

    async def _assign_issue(self, params: dict, headers: dict, domain: str) -> ToolResult:
        issue_key = params["issue_key"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"https://{domain}/rest/api/3/issue/{issue_key}/assignee",
                headers=headers,
                json={"accountId": params["account_id"]},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="assign_issue",
                message=f"Assigned {issue_key} to {params.get('account_id')}",
                url=f"https://{domain}/browse/{issue_key}",
            )

    async def _add_label(self, params: dict, headers: dict, domain: str) -> ToolResult:
        issue_key = params["issue_key"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"https://{domain}/rest/api/3/issue/{issue_key}",
                headers=headers,
                json={"update": {"labels": [{"add": label} for label in params["labels"]]}},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="add_label",
                message=f"Added labels {params['labels']} to {issue_key}",
                url=f"https://{domain}/browse/{issue_key}",
            )

    async def _update_priority(self, params: dict, headers: dict, domain: str) -> ToolResult:
        issue_key = params["issue_key"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"https://{domain}/rest/api/3/issue/{issue_key}",
                headers=headers,
                json={"fields": {"priority": {"name": params["priority"]}}},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="update_priority",
                message=f"Updated {issue_key} priority to {params['priority']}",
                url=f"https://{domain}/browse/{issue_key}",
            )
