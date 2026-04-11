"""Slack tool adapter — post messages and manage channels via Slack API."""

import logging
from typing import Any

import httpx

from app.services.tool_adapters.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SlackTool(BaseTool):
    name = "slack"
    supported_actions = [
        "post_message",
        "reply_to_thread",
        "set_topic",
    ]

    async def execute(self, action: str, params: dict[str, Any], config: dict) -> ToolResult:
        self._validate_action(action)
        token = config.get("token") or config.get("access_token", "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        dispatch = {
            "post_message": self._post_message,
            "reply_to_thread": self._reply_to_thread,
            "set_topic": self._set_topic,
        }
        return await dispatch[action](params, headers)

    async def _post_message(self, params: dict, headers: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json={
                    "channel": params["channel"],
                    "text": params["text"],
                    "unfurl_links": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return ToolResult(
                    success=False,
                    action="post_message",
                    message=f"Slack error: {data.get('error', 'unknown')}",
                )
            return ToolResult(
                success=True,
                action="post_message",
                message=f"Posted message to {params['channel']}",
                data={"ts": data.get("ts"), "channel": data.get("channel")},
            )

    async def _reply_to_thread(self, params: dict, headers: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json={
                    "channel": params["channel"],
                    "text": params["text"],
                    "thread_ts": params["thread_ts"],
                    "unfurl_links": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return ToolResult(
                    success=False,
                    action="reply_to_thread",
                    message=f"Slack error: {data.get('error', 'unknown')}",
                )
            return ToolResult(
                success=True,
                action="reply_to_thread",
                message=f"Replied to thread in {params['channel']}",
                data={"ts": data.get("ts")},
            )

    async def _set_topic(self, params: dict, headers: dict) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://slack.com/api/conversations.setTopic",
                headers=headers,
                json={
                    "channel": params["channel"],
                    "topic": params["topic"],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return ToolResult(
                    success=False,
                    action="set_topic",
                    message=f"Slack error: {data.get('error', 'unknown')}",
                )
            return ToolResult(
                success=True,
                action="set_topic",
                message=f"Set topic for {params['channel']}",
            )
