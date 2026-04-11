"""GitHub tool adapter — create issues, comments, and PRs via GitHub API."""

import logging
from typing import Any

import httpx

from app.services.tool_adapters.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GitHubTool(BaseTool):
    name = "github"
    supported_actions = [
        "create_issue",
        "comment_on_issue",
        "close_issue",
        "create_pull_request",
        "add_label",
        "request_review",
    ]

    async def execute(self, action: str, params: dict[str, Any], config: dict) -> ToolResult:
        self._validate_action(action)
        token = config.get("token") or config.get("access_token", "")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        dispatch = {
            "create_issue": self._create_issue,
            "comment_on_issue": self._comment_on_issue,
            "close_issue": self._close_issue,
            "create_pull_request": self._create_pull_request,
            "add_label": self._add_label,
            "request_review": self._request_review,
        }
        return await dispatch[action](params, headers)

    async def _create_issue(self, params: dict, headers: dict) -> ToolResult:
        repo = params["repo"]  # "owner/repo"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/issues",
                headers=headers,
                json={
                    "title": params["title"],
                    "body": params.get("body", ""),
                    "labels": params.get("labels", []),
                    "assignees": params.get("assignees", []),
                },
            )
            resp.raise_for_status()
            issue = resp.json()
            return ToolResult(
                success=True,
                action="create_issue",
                message=f"Created issue #{issue['number']}: {issue['title']}",
                data={"number": issue["number"], "id": issue["id"]},
                url=issue["html_url"],
            )

    async def _comment_on_issue(self, params: dict, headers: dict) -> ToolResult:
        repo = params["repo"]
        issue_number = params["issue_number"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
                headers=headers,
                json={"body": params["body"]},
            )
            resp.raise_for_status()
            comment = resp.json()
            return ToolResult(
                success=True,
                action="comment_on_issue",
                message=f"Commented on issue #{issue_number}",
                data={"comment_id": comment["id"]},
                url=comment["html_url"],
            )

    async def _close_issue(self, params: dict, headers: dict) -> ToolResult:
        repo = params["repo"]
        issue_number = params["issue_number"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"https://api.github.com/repos/{repo}/issues/{issue_number}",
                headers=headers,
                json={"state": "closed"},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="close_issue",
                message=f"Closed issue #{issue_number}",
                url=resp.json()["html_url"],
            )

    async def _create_pull_request(self, params: dict, headers: dict) -> ToolResult:
        repo = params["repo"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/pulls",
                headers=headers,
                json={
                    "title": params["title"],
                    "body": params.get("body", ""),
                    "head": params["head"],
                    "base": params.get("base", "main"),
                },
            )
            resp.raise_for_status()
            pr = resp.json()
            return ToolResult(
                success=True,
                action="create_pull_request",
                message=f"Created PR #{pr['number']}: {pr['title']}",
                data={"number": pr["number"], "id": pr["id"]},
                url=pr["html_url"],
            )

    async def _add_label(self, params: dict, headers: dict) -> ToolResult:
        repo = params["repo"]
        issue_number = params["issue_number"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/issues/{issue_number}/labels",
                headers=headers,
                json={"labels": params["labels"]},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="add_label",
                message=f"Added labels {params['labels']} to #{issue_number}",
            )

    async def _request_review(self, params: dict, headers: dict) -> ToolResult:
        repo = params["repo"]
        pr_number = params["pr_number"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/pulls/{pr_number}/requested_reviewers",
                headers=headers,
                json={"reviewers": params["reviewers"]},
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="request_review",
                message=f"Requested review from {params['reviewers']} on PR #{pr_number}",
            )
