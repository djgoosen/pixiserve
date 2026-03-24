"""Inbound webhooks (Clerk / Svix)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.config import get_settings
from app.database import get_db
from app.services.clerk_webhook_sync import upsert_user_from_clerk_data

router = APIRouter()
logger = logging.getLogger(__name__)

HANDLED_EVENT_TYPES = frozenset({"user.created", "user.updated"})


def _svix_headers_from_request(request: Request) -> dict[str, str]:
    return {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Clerk user sync webhook (Svix-signed).

    Handles `user.created` and `user.updated` idempotently. Other event types are
    acknowledged without side effects.
    """
    settings = get_settings()
    raw = await request.body()
    try:
        body_str = raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("clerk_webhook_invalid_body_encoding")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid body encoding",
        ) from None

    headers = _svix_headers_from_request(request)
    wh = Webhook(settings.clerk_webhook_secret)
    try:
        payload = wh.verify(body_str, headers)
    except WebhookVerificationError:
        logger.warning("clerk_webhook_signature_invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        ) from None

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    event_type = payload.get("type")
    if event_type not in HANDLED_EVENT_TYPES:
        return {"received": True, "handled": False}

    user_data = payload.get("data")
    if not isinstance(user_data, dict):
        logger.warning("clerk_webhook_missing_user_data", extra={"event_type": event_type})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user payload",
        )

    try:
        await upsert_user_from_clerk_data(db, user_data)
    except ValueError as e:
        logger.warning("clerk_webhook_user_payload_invalid", extra={"reason": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user payload",
        ) from None

    return {"received": True, "handled": True}
