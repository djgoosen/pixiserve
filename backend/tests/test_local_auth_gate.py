"""Legacy local username/password endpoints are gated (Clerk-only by default)."""

from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1 import auth


@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Avoid importing full app (storage/S3 stack) for these route tests."""
    yield


def _make_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    return app


@pytest.fixture
def client():
    app = _make_app()
    with TestClient(app) as c:
        yield c


def test_login_forbidden_when_local_password_auth_disabled(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "u", "password": "p"},
    )
    assert r.status_code == 403
    assert "Clerk" in r.json()["detail"]


def test_register_forbidden_when_local_password_auth_disabled(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": "usr",
            "email": "usr@example.com",
            "password": "password12",
            "name": "Usr",
        },
    )
    assert r.status_code == 403
    assert "ALLOW_LOCAL_PASSWORD_AUTH" in r.json()["detail"]


def test_change_password_forbidden_when_local_password_auth_disabled():
    async def fake_user():
        u = MagicMock()
        u.is_active = True
        return u

    app = _make_app()
    app.dependency_overrides[deps.get_current_user] = fake_user
    try:
        with TestClient(app) as c:
            r = c.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "oldpass12",
                    "new_password": "newpass123",
                },
            )
        assert r.status_code == 403
        assert "Clerk" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
