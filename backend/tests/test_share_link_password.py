"""Share link password hashing, bcrypt verification, and legacy plaintext migration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.auth_service import verify_password
from app.services.share_link_password import (
    SharePasswordCheck,
    check_share_link_password,
    hash_link_password,
    is_bcrypt_password_hash,
)


def test_hash_link_password_none_and_empty():
    assert hash_link_password(None) is None
    assert hash_link_password("") is None


def test_hash_link_password_produces_bcrypt():
    h = hash_link_password("correct-horse-battery")
    assert h is not None
    assert is_bcrypt_password_hash(h)
    assert verify_password("correct-horse-battery", h)


def test_is_bcrypt_password_hash():
    assert is_bcrypt_password_hash("$2b$04$" + "x" * 53)  # shape only
    assert not is_bcrypt_password_hash("plaintext")
    assert not is_bcrypt_password_hash("")


@pytest.mark.asyncio
async def test_check_bcrypt_correct_and_wrong():
    from app.models.album import AlbumShare

    db = AsyncMock()
    share = MagicMock(spec=AlbumShare)
    share.link_password = hash_link_password("secret")

    assert await check_share_link_password(db, share, None) == SharePasswordCheck.REQUIRED_MISSING
    assert await check_share_link_password(db, share, "") == SharePasswordCheck.REQUIRED_MISSING
    assert await check_share_link_password(db, share, "wrong") == SharePasswordCheck.INVALID
    assert await check_share_link_password(db, share, "secret") == SharePasswordCheck.OK
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_no_password_required():
    from app.models.album import AlbumShare

    db = AsyncMock()
    share = MagicMock(spec=AlbumShare)
    share.link_password = None

    assert await check_share_link_password(db, share, None) == SharePasswordCheck.NOT_REQUIRED
    assert await check_share_link_password(db, share, "extra") == SharePasswordCheck.NOT_REQUIRED


@pytest.mark.asyncio
async def test_legacy_plaintext_migrates_on_success():
    from app.models.album import AlbumShare

    db = AsyncMock()
    share = MagicMock(spec=AlbumShare)
    share.link_password = "legacy-plain"

    result = await check_share_link_password(db, share, "legacy-plain")
    assert result == SharePasswordCheck.OK
    assert share.link_password != "legacy-plain"
    assert is_bcrypt_password_hash(share.link_password)
    assert verify_password("legacy-plain", share.link_password)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_legacy_plaintext_wrong_password():
    from app.models.album import AlbumShare

    db = AsyncMock()
    share = MagicMock(spec=AlbumShare)
    share.link_password = "legacy-plain"

    assert await check_share_link_password(db, share, "nope") == SharePasswordCheck.INVALID
    assert share.link_password == "legacy-plain"
    db.flush.assert_not_awaited()
