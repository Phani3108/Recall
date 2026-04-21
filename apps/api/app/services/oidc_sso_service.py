"""OpenID Connect discovery and token helpers for org SSO login."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwt

from app.config import settings
from app.services.oauth_service import sign_oauth_state, verify_oauth_state

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {}
_CACHE_TS: float = 0.0
CACHE_TTL = 3600.0


async def fetch_oidc_configuration(issuer: str) -> dict[str, Any]:
    """Fetch OpenID Provider metadata (cached in-process)."""
    global _CACHE, _CACHE_TS
    issuer = issuer.rstrip("/")
    now = time.time()
    if _CACHE.get("issuer") == issuer and now - _CACHE_TS < CACHE_TTL:
        return _CACHE["doc"]

    well_known = f"{issuer}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(well_known)
        resp.raise_for_status()
        doc = resp.json()

    _CACHE = {"issuer": issuer, "doc": doc}
    _CACHE_TS = now
    return doc


def oidc_sso_configured() -> bool:
    return bool(
        settings.oidc_issuer_url.strip()
        and settings.oidc_client_id.strip()
        and settings.oidc_client_secret.strip()
    )


def build_oidc_authorize_url(authorization_endpoint: str, state: str, nonce: str) -> str:
    redirect_uri = f"{settings.api_url.rstrip('/')}{settings.oidc_redirect_path}"
    params = {
        "client_id": settings.oidc_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
        "nonce": nonce,
    }
    return f"{authorization_endpoint}?{urlencode(params)}"


async def exchange_oidc_code(code: str, token_endpoint: str, redirect_uri: str) -> dict[str, Any]:
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.oidc_client_id,
        "client_secret": settings.oidc_client_secret,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            token_endpoint,
            data=body,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def claims_from_id_token(id_token: str) -> dict[str, Any]:
    """Parse JWT claims without signature verification.

    The token was received over TLS from the issuer token endpoint; for production,
    add JWKS signature verification using the issuer's ``jwks_uri``.
    """
    try:
        return jwt.get_unverified_claims(id_token)
    except Exception as e:
        logger.warning("Failed to parse id_token: %s", e)
        return {}


def verify_oidc_login_state(state: str) -> dict[str, Any] | None:
    """Decode signed OIDC state (nonce + timestamp)."""
    return verify_oauth_state(state)


def sign_oidc_state(nonce: str) -> str:
    """Create signed OIDC login state."""
    return sign_oauth_state({"kind": "oidc", "nonce": nonce, "ts": int(time.time())})
