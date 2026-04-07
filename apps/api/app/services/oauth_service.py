"""OAuth 2.0 service — generates authorization URLs and exchanges codes for access tokens.

Each OAuth provider has:
- authorize_url: where to redirect users for consent
- token_url: where to exchange auth codes for tokens
- scopes: what access we request
- client_id/client_secret: from environment config
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# State signing key (uses app secret)
_STATE_KEY = settings.app_secret_key.encode()


# ── Provider OAuth configurations ──

OAUTH_PROVIDERS: dict[str, dict[str, Any]] = {
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scopes": "repo read:org read:user",
        "client_id_key": "github_client_id",
        "client_secret_key": "github_client_secret",
    },
    "slack": {
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": "channels:read,channels:history,groups:read,chat:write,users:read",
        "client_id_key": "slack_client_id",
        "client_secret_key": "slack_client_secret",
    },
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly",
        "client_id_key": "google_client_id",
        "client_secret_key": "google_client_secret",
        "extra_params": {"access_type": "offline", "prompt": "consent"},
    },
    "notion": {
        "authorize_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "scopes": "",
        "client_id_key": "notion_client_id",
        "client_secret_key": "notion_client_secret",
        "token_auth": "basic",  # Notion uses Basic auth for token exchange
    },
    "jira": {
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "scopes": "read:jira-work read:jira-user offline_access",
        "client_id_key": "atlassian_client_id",
        "client_secret_key": "atlassian_client_secret",
        "extra_params": {"audience": "api.atlassian.com", "prompt": "consent"},
    },
    "confluence": {
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "scopes": "read:confluence-content.all read:confluence-space.summary offline_access",
        "client_id_key": "atlassian_client_id",
        "client_secret_key": "atlassian_client_secret",
        "extra_params": {"audience": "api.atlassian.com", "prompt": "consent"},
    },
    "microsoft365": {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": "Mail.Read Files.Read.All Calendars.Read User.Read offline_access",
        "client_id_key": "microsoft_client_id",
        "client_secret_key": "microsoft_client_secret",
    },
    "linear": {
        "authorize_url": "https://linear.app/oauth/authorize",
        "token_url": "https://api.linear.app/oauth/token",
        "scopes": "read",
        "client_id_key": "linear_client_id",
        "client_secret_key": "linear_client_secret",
    },
    "gitlab": {
        "authorize_url": "https://gitlab.com/oauth/authorize",
        "token_url": "https://gitlab.com/oauth/token",
        "scopes": "read_api read_user read_repository",
        "client_id_key": "gitlab_client_id",
        "client_secret_key": "gitlab_client_secret",
    },
    "zoom": {
        "authorize_url": "https://zoom.us/oauth/authorize",
        "token_url": "https://zoom.us/oauth/token",
        "scopes": "meeting:read user:read recording:read",
        "client_id_key": "zoom_client_id",
        "client_secret_key": "zoom_client_secret",
        "token_auth": "basic",
    },
    "dropbox": {
        "authorize_url": "https://www.dropbox.com/oauth2/authorize",
        "token_url": "https://api.dropboxapi.com/oauth2/token",
        "scopes": "files.metadata.read files.content.read",
        "client_id_key": "dropbox_client_id",
        "client_secret_key": "dropbox_client_secret",
        "extra_params": {"token_access_type": "offline"},
    },
    "figma": {
        "authorize_url": "https://www.figma.com/oauth",
        "token_url": "https://api.figma.com/v1/oauth/token",  # uses www for auth, api for token
        "scopes": "files:read",
        "client_id_key": "figma_client_id",
        "client_secret_key": "figma_client_secret",
    },
    "asana": {
        "authorize_url": "https://app.asana.com/-/oauth_authorize",
        "token_url": "https://app.asana.com/-/oauth_token",
        "scopes": "default",
        "client_id_key": "asana_client_id",
        "client_secret_key": "asana_client_secret",
    },
    "hubspot": {
        "authorize_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "scopes": "crm.objects.contacts.read crm.objects.deals.read",
        "client_id_key": "hubspot_client_id",
        "client_secret_key": "hubspot_client_secret",
    },
}

# Providers that ONLY support API key (no OAuth)
API_KEY_PROVIDERS = {"claude"}

# Providers marked "coming soon" with no connection method yet
COMING_SOON_PROVIDERS = {"whatsapp", "cursor"}


def _get_credentials(provider: str) -> tuple[str, str]:
    """Get client_id and client_secret for a provider from settings."""
    cfg = OAUTH_PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"No OAuth config for {provider}")
    client_id = getattr(settings, cfg["client_id_key"], "")
    client_secret = getattr(settings, cfg["client_secret_key"], "")
    return client_id, client_secret


def is_oauth_configured(provider: str) -> bool:
    """Check if OAuth credentials are set for a provider."""
    if provider in API_KEY_PROVIDERS or provider in COMING_SOON_PROVIDERS:
        return False
    try:
        cid, csec = _get_credentials(provider)
        return bool(cid and csec)
    except ValueError:
        return False


def _sign_state(payload: dict) -> str:
    """Create HMAC-signed state parameter."""
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(_STATE_KEY, data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{data}|{sig}"


def _verify_state(state: str) -> dict | None:
    """Verify and decode a signed state parameter."""
    try:
        data_str, sig = state.rsplit("|", 1)
        expected = hmac.new(_STATE_KEY, data_str.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data_str)
        # Reject states older than 10 minutes
        if time.time() - payload.get("ts", 0) > 600:
            return None
        return payload
    except Exception:
        return None


def generate_auth_url(
    provider: str,
    user_id: str,
    org_id: str,
    redirect_base: str | None = None,
) -> str:
    """Generate OAuth authorization URL for a provider."""
    cfg = OAUTH_PROVIDERS[provider]
    client_id, _ = _get_credentials(provider)

    if not client_id:
        raise ValueError(f"OAuth not configured for {provider} — set {cfg['client_id_key']}")

    base = redirect_base or settings.api_url
    callback_url = f"{base}/api/integrations/oauth/callback/{provider}"

    state = _sign_state({
        "p": provider,
        "u": user_id,
        "o": org_id,
        "ts": int(time.time()),
    })

    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "state": state,
        "response_type": "code",
    }

    if cfg["scopes"]:
        params["scope"] = cfg["scopes"]

    params.update(cfg.get("extra_params", {}))

    return f"{cfg['authorize_url']}?{urlencode(params)}"


async def exchange_code(provider: str, code: str, redirect_base: str | None = None) -> dict:
    """Exchange an authorization code for an access token.

    Returns dict with at least {"access_token": "..."} on success.
    """
    cfg = OAUTH_PROVIDERS[provider]
    client_id, client_secret = _get_credentials(provider)

    base = redirect_base or settings.api_url
    callback_url = f"{base}/api/integrations/oauth/callback/{provider}"

    body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": callback_url,
        "grant_type": "authorization_code",
    }

    headers: dict[str, str] = {"Accept": "application/json"}

    # Some providers require Basic auth for token exchange
    auth = None
    if cfg.get("token_auth") == "basic":
        import base64
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
        body.pop("client_secret", None)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(cfg["token_url"], data=body, headers=headers, auth=auth)
        resp.raise_for_status()
        data = resp.json()

    # Normalize — GitHub returns token in different field names sometimes
    token = data.get("access_token") or data.get("token")
    if not token:
        raise ValueError(f"No access_token in response: {list(data.keys())}")

    return {
        "access_token": token,
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "token_type": data.get("token_type", "bearer"),
        "scope": data.get("scope", ""),
    }


def verify_oauth_state(state: str) -> dict | None:
    """Public wrapper for state verification."""
    return _verify_state(state)


def get_provider_auth_method(provider: str) -> str:
    """Return 'oauth', 'api_key', or 'coming_soon' for a provider."""
    if provider in COMING_SOON_PROVIDERS:
        return "coming_soon"
    if provider in API_KEY_PROVIDERS:
        return "api_key"
    if provider in OAUTH_PROVIDERS:
        return "oauth"
    return "api_key"  # fallback
