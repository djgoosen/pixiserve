"""Clerk → local User sync (upsert, FR-AUTH-02 first admin)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.clerk_webhook_sync import upsert_user_from_clerk_data

_CLERK_USER_A = {
    "id": "user_pin003_a",
    "email_addresses": [{"id": "ea1", "email_address": "alpha@example.com"}],
    "primary_email_address_id": "ea1",
    "first_name": "Al",
    "last_name": "Pha",
}

_CLERK_USER_B = {
    "id": "user_pin003_b",
    "email_addresses": [{"id": "eb1", "email_address": "beta@example.com"}],
    "primary_email_address_id": "eb1",
}


@pytest.mark.asyncio
async def test_upsert_first_clerk_user_is_admin():
    db = AsyncMock()
    db.add = MagicMock()
    instance = MagicMock()
    instance.is_admin = True

    with (
        patch("app.services.clerk_webhook_sync.User", return_value=instance) as UserCls,
        patch(
            "app.services.clerk_webhook_sync.get_user_by_clerk_user_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.services.clerk_webhook_sync.get_user_by_username",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.services.clerk_webhook_sync.get_user_count",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        user = await upsert_user_from_clerk_data(db, _CLERK_USER_A)

    UserCls.assert_called_once()
    assert UserCls.call_args.kwargs["is_admin"] is True
    assert UserCls.call_args.kwargs["clerk_user_id"] == "user_pin003_a"
    assert user is instance
    db.add.assert_called_once_with(instance)
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_upsert_second_clerk_user_not_admin():
    db = AsyncMock()
    db.add = MagicMock()
    instance = MagicMock()
    instance.is_admin = False

    with (
        patch("app.services.clerk_webhook_sync.User", return_value=instance) as UserCls,
        patch(
            "app.services.clerk_webhook_sync.get_user_by_clerk_user_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.services.clerk_webhook_sync.get_user_by_username",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.services.clerk_webhook_sync.get_user_count",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        await upsert_user_from_clerk_data(db, _CLERK_USER_B)

    UserCls.assert_called_once()
    assert UserCls.call_args.kwargs["is_admin"] is False
    db.add.assert_called_once_with(instance)
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_upsert_updates_existing_by_clerk_id_no_second_row():
    db = AsyncMock()
    db.add = MagicMock()
    existing = MagicMock()
    existing.clerk_user_id = "user_pin003_a"
    existing.email = "old@example.com"
    existing.name = "Old"

    with patch(
        "app.services.clerk_webhook_sync.get_user_by_clerk_user_id",
        new_callable=AsyncMock,
        return_value=existing,
    ):
        user = await upsert_user_from_clerk_data(db, _CLERK_USER_A)

    assert user is existing
    assert existing.email == "alpha@example.com"
    assert existing.name == "Al Pha"
    db.add.assert_not_called()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_upsert_idempotent_replay_same_event_updates_once():
    """Second delivery of the same Clerk user hits the update branch (no duplicate add)."""
    db = AsyncMock()
    db.add = MagicMock()
    existing = MagicMock()
    existing.clerk_user_id = "user_pin003_a"
    existing.email = "alpha@example.com"
    existing.name = "Al Pha"

    with patch(
        "app.services.clerk_webhook_sync.get_user_by_clerk_user_id",
        new_callable=AsyncMock,
        return_value=existing,
    ):
        await upsert_user_from_clerk_data(db, _CLERK_USER_A)

    db.add.assert_not_called()
    assert db.commit.await_count == 1
