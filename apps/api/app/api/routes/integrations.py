import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Integration, IntegrationProvider, IntegrationStatus
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import IntegrationCreate, IntegrationResponse
from app.services import integration_hub

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
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initiate OAuth flow for an integration via Composio."""
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

    try:
        connection = await integration_hub.initiate_connection(
            provider=integration.provider.value,
            org_id=ctx.org_id,
            user_id=ctx.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.error("Failed to initiate OAuth", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to initiate connection with provider")

    # Store Composio connection ID for later lookup
    integration.config = integration.config or {}
    integration.config["composio_connection_id"] = connection["connection_id"]
    integration.status = IntegrationStatus.PENDING
    await db.flush()

    return {"redirect_url": connection["redirect_url"]}


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(
    integration_id: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disconnect an active integration."""
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

    connection_id = (integration.config or {}).get("composio_connection_id")
    if connection_id:
        try:
            await integration_hub.disconnect(connection_id)
        except Exception:
            logger.warning("Failed to disconnect from Composio", exc_info=True)

    integration.status = IntegrationStatus.DISCONNECTED
    await db.flush()

    return {"status": "disconnected"}


@router.get("/{integration_id}/status")
async def check_integration_status(
    integration_id: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check current status of an integration's OAuth connection."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.org_id == ctx.org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    connection_id = (integration.config or {}).get("composio_connection_id")
    if not connection_id:
        return {"status": integration.status.value, "provider": integration.provider.value}

    try:
        status = await integration_hub.get_connection_status(connection_id)

        # Update local status to match Composio
        if status["status"] == "ACTIVE":
            integration.status = IntegrationStatus.ACTIVE
        elif status["status"] == "FAILED":
            integration.status = IntegrationStatus.ERROR

        await db.flush()

        return {
            "status": integration.status.value,
            "provider": integration.provider.value,
            "remote_status": status["status"],
        }
    except Exception:
        logger.warning("Failed to check Composio status", exc_info=True)
        return {"status": integration.status.value, "provider": integration.provider.value}
