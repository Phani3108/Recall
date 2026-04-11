"""Confluence tool adapter — create/update pages, add comments via Confluence API."""

import base64
import logging
from typing import Any

import httpx

from app.services.tool_adapters.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ConfluenceTool(BaseTool):
    name = "confluence"
    supported_actions = [
        "create_page",
        "update_page",
        "add_comment",
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
            "create_page": self._create_page,
            "update_page": self._update_page,
            "add_comment": self._add_comment,
        }
        return await dispatch[action](params, headers, domain)

    async def _create_page(self, params: dict, headers: dict, domain: str) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://{domain}/wiki/api/v2/pages",
                headers=headers,
                json={
                    "spaceId": params["space_id"],
                    "status": "current",
                    "title": params["title"],
                    "body": {
                        "representation": "storage",
                        "value": params.get("body", ""),
                    },
                },
            )
            resp.raise_for_status()
            page = resp.json()
            webui = page.get("_links", {}).get("webui", "")
            return ToolResult(
                success=True,
                action="create_page",
                message=f"Created page: {params['title']}",
                data={"page_id": page["id"]},
                url=f"https://{domain}/wiki{webui}",
            )

    async def _update_page(self, params: dict, headers: dict, domain: str) -> ToolResult:
        page_id = params["page_id"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get current version
            get_resp = await client.get(
                f"https://{domain}/wiki/api/v2/pages/{page_id}",
                headers=headers,
            )
            get_resp.raise_for_status()
            current = get_resp.json()
            current_version = current.get("version", {}).get("number", 1)

            resp = await client.put(
                f"https://{domain}/wiki/api/v2/pages/{page_id}",
                headers=headers,
                json={
                    "id": page_id,
                    "status": "current",
                    "title": params.get("title", current.get("title", "")),
                    "body": {
                        "representation": "storage",
                        "value": params["body"],
                    },
                    "version": {"number": current_version + 1},
                },
            )
            resp.raise_for_status()
            page = resp.json()
            webui = page.get("_links", {}).get("webui", "")
            return ToolResult(
                success=True,
                action="update_page",
                message=f"Updated page: {page.get('title', page_id)}",
                data={"page_id": page_id, "version": current_version + 1},
                url=f"https://{domain}/wiki{webui}",
            )

    async def _add_comment(self, params: dict, headers: dict, domain: str) -> ToolResult:
        page_id = params["page_id"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://{domain}/wiki/api/v2/pages/{page_id}/footer-comments",
                headers=headers,
                json={
                    "body": {
                        "representation": "storage",
                        "value": f"<p>{params['body']}</p>",
                    },
                },
            )
            resp.raise_for_status()
            return ToolResult(
                success=True,
                action="add_comment",
                message=f"Added comment to page {page_id}",
            )
