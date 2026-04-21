"""Stripe Checkout for org subscription (owner-only)."""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context
from app.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/checkout-session")
async def create_checkout_session(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a Stripe Checkout Session for the current org (subscription mode)."""
    ctx.require_role("owner")

    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured (set STRIPE_SECRET_KEY and STRIPE_PRICE_ID)",
        )

    stripe.api_key = settings.stripe_secret_key
    org = ctx.org

    if not org.stripe_customer_id:
        customer = stripe.Customer.create(
            email=ctx.user.email,
            metadata={"org_id": str(org.id), "user_id": str(ctx.user_id)},
        )
        org.stripe_customer_id = customer.id
        await db.flush()

    try:
        session = stripe.checkout.Session.create(
            customer=org.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.frontend_url.rstrip('/')}/app/settings?billing=success",
            cancel_url=f"{settings.frontend_url.rstrip('/')}/app/settings?billing=cancel",
            client_reference_id=str(org.id),
            metadata={"org_id": str(org.id)},
        )
    except Exception as e:
        logger.warning("Stripe checkout error: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    await db.commit()
    return {"url": session.url}


@router.get("/status")
async def billing_status(ctx: OrgContext = Depends(get_org_context)) -> dict:
    ctx.require_role("owner", "admin")
    org = ctx.org
    return {
        "stripe_customer_id": org.stripe_customer_id,
        "stripe_subscription_id": org.stripe_subscription_id,
        "subscription_status": org.subscription_status or "none",
        "checkout_configured": bool(settings.stripe_secret_key and settings.stripe_price_id),
    }
