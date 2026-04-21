"""Stripe webhooks — subscription lifecycle (no JWT)."""

import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Organization
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    if not settings.stripe_webhook_secret or not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe webhooks are not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except Exception as e:
        if "SignatureVerification" in type(e).__name__:
            raise HTTPException(status_code=400, detail="Invalid signature") from e
        raise

    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        org_id_raw = (obj.get("metadata") or {}).get("org_id") or obj.get("client_reference_id")
        if org_id_raw:
            try:
                org_id = uuid.UUID(str(org_id_raw))
            except ValueError:
                org_id = None
            if org_id:
                res = await db.execute(select(Organization).where(Organization.id == org_id))
                org = res.scalar_one_or_none()
                if org:
                    org.stripe_customer_id = org.stripe_customer_id or obj.get("customer")
                    org.stripe_subscription_id = obj.get("subscription")
                    org.subscription_status = "incomplete"
                    await db.commit()

    elif etype in (
        "customer.subscription.updated",
        "customer.subscription.created",
    ):
        sub_id = obj.get("id")
        status = obj.get("status", "none")
        cust = obj.get("customer")
        if cust and sub_id:
            res = await db.execute(select(Organization).where(Organization.stripe_customer_id == cust))
            org = res.scalar_one_or_none()
            if org:
                org.stripe_subscription_id = sub_id
                org.subscription_status = status or "none"
                await db.commit()

    elif etype == "customer.subscription.deleted":
        sub_id = obj.get("id")
        cust = obj.get("customer")
        if cust:
            res = await db.execute(select(Organization).where(Organization.stripe_customer_id == cust))
            org = res.scalar_one_or_none()
            if org and org.stripe_subscription_id == sub_id:
                org.subscription_status = "canceled"
                org.stripe_subscription_id = None
                await db.commit()

    return {"received": True}
