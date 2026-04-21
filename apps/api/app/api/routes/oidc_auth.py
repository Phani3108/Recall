"""OIDC SSO — browser login via configured identity provider."""

import logging
import re
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import create_access_token
from app.db.models import Organization, OrgMembership, OrgRole, User
from app.db.session import get_db
from app.config import settings
from app.services.oidc_sso_service import (
    build_oidc_authorize_url,
    claims_from_id_token,
    exchange_oidc_code,
    fetch_oidc_configuration,
    oidc_sso_configured,
    sign_oidc_state,
    verify_oidc_login_state,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _slug_from_email(email: str) -> str:
    local = email.split("@")[0].lower()
    safe = re.sub(r"[^a-z0-9-]+", "-", local).strip("-")[:40] or "org"
    return f"{safe}-{uuid.uuid4().hex[:6]}"


@router.get("/login")
async def oidc_login_start() -> RedirectResponse:
    if not oidc_sso_configured():
        raise HTTPException(status_code=503, detail="OIDC SSO is not configured on this server")

    doc = await fetch_oidc_configuration(settings.oidc_issuer_url)
    nonce = secrets.token_urlsafe(16)
    state = sign_oidc_state(nonce)
    url = build_oidc_authorize_url(doc["authorization_endpoint"], state, nonce)
    return RedirectResponse(url, status_code=302)


@router.get("/callback")
async def oidc_login_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if error:
        return RedirectResponse(
            f"{settings.frontend_url.rstrip('/')}/login?error={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    payload = verify_oidc_login_state(state)
    if not payload or payload.get("kind") != "oidc":
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    doc = await fetch_oidc_configuration(settings.oidc_issuer_url)
    redirect_uri = f"{settings.api_url.rstrip('/')}{settings.oidc_redirect_path}"

    try:
        tokens = await exchange_oidc_code(code, doc["token_endpoint"], redirect_uri)
    except Exception as e:
        logger.warning("OIDC token exchange failed: %s", e)
        raise HTTPException(status_code=400, detail="Token exchange failed") from e

    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No id_token in token response")

    claims = claims_from_id_token(id_token)
    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Identity token has no email claim")

    name = str(claims.get("name") or claims.get("given_name") or email.split("@")[0])
    sub = str(claims.get("sub") or "")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if sub and not user.external_id:
            user.external_id = sub[:255]
    else:
        user = User(
            email=email,
            name=name[:255],
            password_hash=None,
            external_id=sub[:255] if sub else None,
        )
        db.add(user)
        await db.flush()

        org = Organization(name=f"{(name or 'User').split()[0]}'s workspace", slug=_slug_from_email(email))
        db.add(org)
        await db.flush()
        db.add(OrgMembership(user_id=user.id, org_id=org.id, role=OrgRole.OWNER))

    mres = await db.execute(select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1))
    membership = mres.scalar_one_or_none()
    if not membership:
        org = Organization(
            name=f"{(user.name or 'User').split()[0]}'s workspace",
            slug=_slug_from_email(user.email),
        )
        db.add(org)
        await db.flush()
        db.add(OrgMembership(user_id=user.id, org_id=org.id, role=OrgRole.OWNER))
        org_id = org.id
    else:
        org_id = membership.org_id

    await db.commit()

    token = create_access_token(user.id, org_id)
    return RedirectResponse(
        f"{settings.frontend_url.rstrip('/')}/login?access_token={token}",
        status_code=302,
    )
