from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Organization, OrgMembership, User
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import (
    OrgResponse,
    OrgMemberResponse,
    PlatformKeysUpdate,
    PlatformKeysResponse,
    LicenseActivateRequest,
    LicenseResponse,
    OrgSettingsResponse,
)

router = APIRouter()


def _mask_key(key: str | None) -> str | None:
    """Return masked version: first 4 + last 4 chars, rest replaced with ***."""
    if not key:
        return None
    if len(key) <= 12:
        return key[:3] + "***" + key[-3:]
    return key[:4] + "***" + key[-4:]


@router.get("/current", response_model=OrgResponse)
async def get_current_org(ctx: OrgContext = Depends(get_org_context)) -> OrgResponse:
    org = ctx.org
    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        token_budget_monthly=org.token_budget_monthly,
        tokens_used_this_month=org.tokens_used_this_month,
        created_at=org.created_at,
    )


@router.get("/members", response_model=list[OrgMemberResponse])
async def list_members(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[OrgMemberResponse]:
    result = await db.execute(
        select(OrgMembership, User)
        .join(User, OrgMembership.user_id == User.id)
        .where(OrgMembership.org_id == ctx.org_id)
    )
    rows = result.all()
    return [
        OrgMemberResponse(
            id=membership.id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=membership.role.value,
            joined_at=membership.created_at,
        )
        for membership, user in rows
    ]


# ── Org Settings: API Keys ──


@router.get("/settings", response_model=OrgSettingsResponse)
async def get_org_settings(
    ctx: OrgContext = Depends(get_org_context),
) -> OrgSettingsResponse:
    ctx.require_role("owner", "admin")
    org = ctx.org
    keys = org.platform_keys or {}
    return OrgSettingsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        license=LicenseResponse(
            tier=org.license_tier,
            license_key_set=bool(org.license_key),
            valid_until=org.license_valid_until,
        ),
        platform_keys=PlatformKeysResponse(
            openai_api_key=_mask_key(keys.get("openai_api_key")),
            anthropic_api_key=_mask_key(keys.get("anthropic_api_key")),
            composio_api_key=_mask_key(keys.get("composio_api_key")),
        ),
        token_budget_monthly=org.token_budget_monthly,
        tokens_used_this_month=org.tokens_used_this_month,
    )


@router.put("/settings/platform-keys")
async def update_platform_keys(
    body: PlatformKeysUpdate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
):
    ctx.require_role("owner", "admin")
    org = ctx.org
    keys = dict(org.platform_keys or {})
    # Only update keys that were explicitly sent (non-None)
    if body.openai_api_key is not None:
        keys["openai_api_key"] = body.openai_api_key
    if body.anthropic_api_key is not None:
        keys["anthropic_api_key"] = body.anthropic_api_key
    if body.composio_api_key is not None:
        keys["composio_api_key"] = body.composio_api_key
    org.platform_keys = keys
    db.add(org)
    await db.flush()
    return {
        "status": "saved",
        "platform_keys": PlatformKeysResponse(
            openai_api_key=_mask_key(keys.get("openai_api_key")),
            anthropic_api_key=_mask_key(keys.get("anthropic_api_key")),
            composio_api_key=_mask_key(keys.get("composio_api_key")),
        ),
    }


@router.delete("/settings/platform-keys/{key_name}")
async def remove_platform_key(
    key_name: str,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
):
    ctx.require_role("owner", "admin")
    valid_keys = {"openai_api_key", "anthropic_api_key", "composio_api_key"}
    if key_name not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid key name. Must be one of: {', '.join(valid_keys)}")
    org = ctx.org
    keys = dict(org.platform_keys or {})
    keys.pop(key_name, None)
    org.platform_keys = keys
    db.add(org)
    await db.flush()
    return {"status": "removed", "key_name": key_name}


# ── License ──


@router.post("/settings/activate-license")
async def activate_license(
    body: LicenseActivateRequest,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
):
    ctx.require_role("owner")
    org = ctx.org

    # License validation logic — in production this would call a license server.
    # For now: any key starting with "RECALL-PRO-" → pro, "RECALL-ENT-" → enterprise.
    key = body.license_key.strip()
    if key.startswith("RECALL-ENT-"):
        tier = "enterprise"
    elif key.startswith("RECALL-PRO-"):
        tier = "pro"
    else:
        raise HTTPException(status_code=400, detail="Invalid license key. Contact support@recall.dev.")

    org.license_key = key
    org.license_tier = tier
    org.license_valid_until = datetime.now(UTC) + timedelta(days=365)
    db.add(org)
    await db.flush()
    return LicenseResponse(
        tier=tier,
        license_key_set=True,
        valid_until=org.license_valid_until,
    )
