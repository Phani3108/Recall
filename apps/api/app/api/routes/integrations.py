import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Integration, IntegrationProvider, IntegrationStatus
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import IntegrationCreate, IntegrationConnect, IntegrationResponse
from app.services.sync_service import validate_and_sync, PROVIDER_FIELDS, PROVIDER_HELP_URLS

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.get("/providers/fields")
async def provider_fields() -> dict:
    """Return the credential fields required for each provider (no auth required for this meta endpoint)."""
    return {
        provider: {
            "fields": fields,
            "help_url": PROVIDER_HELP_URLS.get(provider, ""),
        }
        for provider, fields in PROVIDER_FIELDS.items()
    }


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

    # Store credentials in config (tokens are already scoped to user's own accounts)
    integration.config = req.config
    integration.status = IntegrationStatus.SYNCING
    await db.flush()

    # Validate & sync data
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
    """Re-sync data from an already-connected integration."""
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
    """Disconnect an active integration and clear credentials."""
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
    """Check current status of an integration."""
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
