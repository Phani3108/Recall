import json
import logging
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Integration, IntegrationProvider, IntegrationStatus
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import IntegrationCreate, IntegrationConnect, IntegrationResponse
from app.services.sync_service import validate_and_sync, PROVIDER_FIELDS, PROVIDER_HELP_URLS
from app.services.oauth_service import (
    generate_auth_url,
    exchange_code,
    verify_oauth_state,
    is_oauth_configured,
    get_provider_auth_method,
    OAUTH_PROVIDERS,
    API_KEY_PROVIDERS,
    COMING_SOON_PROVIDERS,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Provider metadata (no auth required) ──


@router.get("/providers/fields")
async def provider_fields() -> dict:
    """Return credential fields, help URLs, and auth method for each provider."""
    result = {}
    all_providers = (
        set(PROVIDER_FIELDS.keys())
        | set(OAUTH_PROVIDERS.keys())
        | API_KEY_PROVIDERS
        | COMING_SOON_PROVIDERS
    )
    for provider in sorted(all_providers):
        auth_method = get_provider_auth_method(provider)
        result[provider] = {
            "fields": PROVIDER_FIELDS.get(provider, []),
            "help_url": PROVIDER_HELP_URLS.get(provider, ""),
            "auth_method": auth_method,
            "oauth_configured": is_oauth_configured(provider) if auth_method == "oauth" else False,
        }
    return result


# ── OAuth callback (must be before /{integration_id} routes) ──


@router.get("/oauth/callback/{provider}", response_class=HTMLResponse)
async def oauth_callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Handle OAuth redirect. Exchanges code for token, syncs data,
    then postMessages the opener and auto-closes."""
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    error = request.query_params.get("error")

    if error:
        return _popup_response(success=False, error=error, provider=provider)

    if not code:
        return _popup_response(
            success=False, error="No authorization code received", provider=provider
        )

    payload = verify_oauth_state(state)
    if not payload:
        return _popup_response(
            success=False, error="Invalid or expired authorization state", provider=provider
        )

    if payload.get("p") != provider:
        return _popup_response(success=False, error="Provider mismatch", provider=provider)

    user_id = uuid.UUID(payload["u"])
    org_id = uuid.UUID(payload["o"])

    try:
        token_data = await exchange_code(provider, code)
        access_token = token_data["access_token"]

        result = await db.execute(
            select(Integration).where(
                Integration.org_id == org_id,
                Integration.provider == IntegrationProvider(provider),
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            integration = Integration(
                org_id=org_id,
                provider=IntegrationProvider(provider),
                status=IntegrationStatus.SYNCING,
                connected_by=user_id,
            )
            db.add(integration)
            await db.flush()
        else:
            integration.status = IntegrationStatus.SYNCING
            await db.flush()

        config = {"token": access_token, "access_token": access_token}
        if token_data.get("refresh_token"):
            config["refresh_token"] = token_data["refresh_token"]
        integration.config = config

        sync_result = await validate_and_sync(
            provider=provider,
            config=config,
            org_id=org_id,
            integration_id=integration.id,
            db=db,
        )

        if sync_result["status"] == "ok":
            integration.status = IntegrationStatus.ACTIVE
            integration.last_synced_at = datetime.now(UTC)
        else:
            integration.status = IntegrationStatus.ERROR

        await db.commit()

        return _popup_response(
            success=True, provider=provider, synced=sync_result.get("synced", 0)
        )

    except Exception as e:
        logger.error("OAuth callback failed for %s: %s", provider, e, exc_info=True)
        await db.rollback()
        return _popup_response(success=False, error=str(e), provider=provider)


def _popup_response(
    success: bool,
    provider: str,
    error: str | None = None,
    synced: int = 0,
) -> HTMLResponse:
    """HTML page that postMessages the opener and auto-closes."""
    msg = {
        "type": "recall_oauth_callback",
        "provider": provider,
        "success": success,
        "synced": synced,
    }
    if error:
        msg["error"] = error

    msg_json = json.dumps(msg)
    icon = "&#10003;" if success else "&#10007;"
    err_safe = (error or "unknown").replace("<", "&lt;").replace(">", "&gt;")
    status_text = f"Connected {provider}!" if success else f"Failed: {err_safe}"

    html = (
        "<!DOCTYPE html>"
        "<html><head><title>Recall - OAuth</title></head>"
        '<body style="background:#0f0f23;color:#fff;font-family:system-ui;'
        'display:flex;align-items:center;justify-content:center;height:100vh;margin:0">'
        '<div style="text-align:center">'
        f'<p style="font-size:18px">{icon} {status_text}</p>'
        '<p style="font-size:14px;color:#888">This window will close automatically...</p>'
        "</div>"
        "<script>"
        f"if(window.opener){{window.opener.postMessage({msg_json},'*');}}"
        "setTimeout(function(){window.close();},1500);"
        "</script>"
        "</body></html>"
    )
    return HTMLResponse(content=html)


# ── CRUD ──


@router.get("/", response_model=list[IntegrationResponse])
async def list_integrations(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[IntegrationResponse]:
    result = await db.execute(
        select(Integration).where(Integration.org_id == ctx.org_id)
    )
    integrations = result.scalars().all()
    return [
        IntegrationResponse(
            id=i.id,
            provider=i.provider.value,
            status=i.status.value,
            connected_by=i.connected_by,
            last_synced_at=i.last_synced_at,
            created_at=i.created_at,
        )
        for i in integrations
    ]


@router.post("/", response_model=IntegrationResponse, status_code=201)
async def create_integration(
    req: IntegrationCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> IntegrationResponse:
    ctx.require_role("owner", "admin")

    try:
        provider = IntegrationProvider(req.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}") from e

    integration = Integration(
        org_id=ctx.org_id,
        provider=provider,
        status=IntegrationStatus.DISCONNECTED,
        connected_by=ctx.user_id,
    )
    db.add(integration)
    await db.flush()

    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider.value,
        status=integration.status.value,
        connected_by=integration.connected_by,
        last_synced_at=integration.last_synced_at,
        created_at=integration.created_at,
    )


@router.delete("/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    ctx.require_role("owner", "admin")
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.org_id == ctx.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(integration)


# ── OAuth URL generation ──


@router.get("/{provider}/oauth-url")
async def get_oauth_url(
    provider: str,
    ctx: OrgContext = Depends(get_org_context),
) -> dict:
    """Generate OAuth authorization URL. Frontend opens this in a popup."""
    ctx.require_role("owner", "admin")

    if not is_oauth_configured(provider):
        raise HTTPException(status_code=400, detail=f"OAuth not configured for {provider}")

    url = generate_auth_url(
        provider=provider,
        user_id=str(ctx.user_id),
        org_id=str(ctx.org_id),
    )
    return {"auth_url": url}


# ── Token-based connect (for API-key providers or OAuth fallback) ──


@router.post("/{integration_id}/connect")
async def connect_integration(
    integration_id: str,
    req: IntegrationConnect,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Connect an integration with API credentials and sync initial data."""
    ctx.require_role("owner", "admin")

    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.org_id == ctx.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration.config = req.config
    integration.status = IntegrationStatus.SYNCING
    await db.flush()

    sync_result = await validate_and_sync(
        provider=integration.provider.value,
        config=req.config,
        org_id=ctx.org_id,
        integration_id=integration.id,
        db=db,
    )

    if sync_result["status"] == "ok":
        integration.status = IntegrationStatus.ACTIVE
        integration.last_synced_at = datetime.now(UTC)
    else:
        integration.status = IntegrationStatus.ERROR

    await db.flush()

    return {
        "status": integration.status.value,
        "synced": sync_result.get("synced", 0),
        "error": sync_result.get("error"),
    }


@router.post("/{integration_id}/sync")
async def sync_integration(
    integration_id: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ctx.require_role("owner", "admin")

    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.org_id == ctx.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if not integration.config:
        raise HTTPException(status_code=400, detail="Integration has no credentials configured")

    integration.status = IntegrationStatus.SYNCING
    await db.flush()

    sync_result = await validate_and_sync(
        provider=integration.provider.value,
        config=integration.config,
        org_id=ctx.org_id,
        integration_id=integration.id,
        db=db,
    )

    if sync_result["status"] == "ok":
        integration.status = IntegrationStatus.ACTIVE
        integration.last_synced_at = datetime.now(UTC)
    else:
        integration.status = IntegrationStatus.ERROR

    await db.flush()

    return {
        "status": integration.status.value,
        "synced": sync_result.get("synced", 0),
        "error": sync_result.get("error"),
    }


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(
    integration_id: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ctx.require_role("owner", "admin")

    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.org_id == ctx.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration.config = {}
    integration.status = IntegrationStatus.DISCONNECTED
    await db.flush()

    return {"status": "disconnected"}


@router.get("/{integration_id}/status")
async def check_integration_status(
    integration_id: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.org_id == ctx.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "status": integration.status.value,
        "provider": integration.provider.value,
        "last_synced_at": integration.last_synced_at.isoformat() if integration.last_synced_at else None,
    }
