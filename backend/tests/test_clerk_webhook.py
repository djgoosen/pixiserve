"""Clerk webhook (Svix) verification and routing."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from svix.webhooks import Webhook

from app.api.v1 import webhooks
from app.config import get_settings
from app.database import get_db

TEST_WEBHOOK_SECRET = "whsec_dGVzdF9zZWNyZXRmb3JfaW50ZXJuYWxfdGVzdG9ubHk="


@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Match production Clerk env validation without importing the full app stack."""
    settings = get_settings()
    if not settings.clerk_secret_key.strip():
        raise RuntimeError("CLERK_SECRET_KEY is required.")
    if not settings.clerk_publishable_key.strip():
        raise RuntimeError("CLERK_PUBLISHABLE_KEY is required.")
    if not settings.clerk_webhook_secret.strip():
        raise RuntimeError("CLERK_WEBHOOK_SECRET is required.")
    yield


def _make_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
    return app


def _sign_body(body: dict, msg_id: str = "msg_svix_1") -> tuple[bytes, dict[str, str]]:
    wh = Webhook(TEST_WEBHOOK_SECRET)
    body_str = json.dumps(body, separators=(",", ":"))
    ts = datetime.now(timezone.utc)
    sig = wh.sign(msg_id, ts, body_str)
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": str(int(ts.timestamp())),
        "svix-signature": sig,
        "Content-Type": "application/json",
    }
    return body_str.encode("utf-8"), headers


@pytest.fixture
def client():
    app = _make_app()

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_clerk_webhook_rejects_invalid_signature(client):
    body = {"type": "user.created", "data": {"id": "user_x"}}
    body_str = json.dumps(body, separators=(",", ":"))
    ts = datetime.now(timezone.utc)
    other = Webhook("whsec_dGVzdF9vdGhlcnNlY3JldG90aGVyb25seSE=")
    sig = other.sign("m_bad", ts, body_str)
    r = client.post(
        "/api/v1/webhooks/clerk",
        content=body_str.encode(),
        headers={
            "svix-id": "m_bad",
            "svix-timestamp": str(int(ts.timestamp())),
            "svix-signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid webhook signature"


def test_clerk_webhook_user_created_calls_upsert(client):
    body = {
        "type": "user.created",
        "object": "event",
        "data": {
            "id": "user_wh_ok",
            "email_addresses": [{"id": "e1", "email_address": "u@example.com"}],
            "primary_email_address_id": "e1",
        },
    }
    raw, headers = _sign_body(body)
    with patch(
        "app.api.v1.webhooks.upsert_user_from_clerk_data",
        new_callable=AsyncMock,
    ) as upsert:
        r = client.post("/api/v1/webhooks/clerk", content=raw, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"received": True, "handled": True}
    upsert.assert_awaited_once()


def test_clerk_webhook_ignores_unhandled_event_type(client):
    body = {"type": "session.created", "object": "event", "data": {}}
    raw, headers = _sign_body(body)
    with patch(
        "app.api.v1.webhooks.upsert_user_from_clerk_data",
        new_callable=AsyncMock,
    ) as upsert:
        r = client.post("/api/v1/webhooks/clerk", content=raw, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"received": True, "handled": False}
    upsert.assert_not_awaited()


def test_clerk_webhook_user_created_missing_user_id_returns_400(client):
    body = {"type": "user.created", "object": "event", "data": {"email_addresses": []}}
    raw, headers = _sign_body(body)
    r = client.post("/api/v1/webhooks/clerk", content=raw, headers=headers)
    assert r.status_code == 400
