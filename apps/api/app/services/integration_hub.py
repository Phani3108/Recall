"""Integration Hub — OAuth & data sync for third-party tools.

Uses Composio for managed OAuth flows and webhook-based data ingestion.
Supports: Slack, Google, GitHub, Notion, Jira, Linear, Confluence, GitLab, Microsoft365, Dropbox.
"""

import logging
import uuid
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Composio app name mapping from our IntegrationProvider enum
COMPOSIO_APP_MAP = {
    "slack": "SLACK",
    "google": "GOOGLESHEETS",  # Composio uses specific Google app names
    "github": "GITHUB",
    "notion": "NOTION",
    "jira": "JIRA",
    "linear": "LINEAR",
    "confluence": "CONFLUENCE",
    "gitlab": "GITLAB",
    "microsoft365": "MICROSOFT365",
    "dropbox": "DROPBOX",
}

COMPOSIO_BASE_URL = "https://backend.composio.dev/api/v1"


def _headers() -> dict:
    return {
        "X-API-KEY": settings.composio_api_key,
        "Content-Type": "application/json",
    }


async def initiate_connection(
    provider: str,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    redirect_url: str | None = None,
) -> dict:
    """Start an OAuth flow via Composio.

    Returns: {"redirect_url": "https://...", "connection_id": "..."}
    """
    app_name = COMPOSIO_APP_MAP.get(provider)
    if not app_name:
        raise ValueError(f"Unsupported provider: {provider}")

    entity_id = f"{org_id}:{user_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{COMPOSIO_BASE_URL}/connectedAccounts",
            headers=_headers(),
            json={
                "integrationId": app_name,
                "entityId": entity_id,
                "redirectUri": redirect_url or f"{settings.api_url}/api/v1/integrations/callback",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "redirect_url": data.get("redirectUrl", ""),
        "connection_id": data.get("connectedAccountId", ""),
    }


async def get_connection_status(connection_id: str) -> dict:
    """Check if an OAuth connection is active."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{COMPOSIO_BASE_URL}/connectedAccounts/{connection_id}",
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "status": data.get("status", "unknown"),
        "app_name": data.get("appName", ""),
        "created_at": data.get("createdAt", ""),
    }


async def disconnect(connection_id: str) -> bool:
    """Revoke an OAuth connection."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.delete(
            f"{COMPOSIO_BASE_URL}/connectedAccounts/{connection_id}",
            headers=_headers(),
        )
        return resp.status_code in (200, 204)


async def execute_action(
    connection_id: str,
    action: str,
    params: dict | None = None,
) -> dict:
    """Execute a Composio action on a connected account.

    Examples: GITHUB_GET_REPO, SLACK_SEND_MESSAGE, JIRA_CREATE_ISSUE
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{COMPOSIO_BASE_URL}/actions/{action}/execute",
            headers=_headers(),
            json={
                "connectedAccountId": connection_id,
                "input": params or {},
            },
        )
        resp.raise_for_status()
        return resp.json()


async def list_available_actions(app_name: str) -> list[dict]:
    """List available actions for an app."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{COMPOSIO_BASE_URL}/actions",
            headers=_headers(),
            params={"appNames": app_name, "limit": 50},
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "name": a.get("name", ""),
            "display_name": a.get("displayName", ""),
            "description": a.get("description", ""),
        }
        for a in data.get("items", [])
    ]
