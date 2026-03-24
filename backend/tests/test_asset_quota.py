import io
import sys
import types
from types import SimpleNamespace
from uuid import uuid4

import pytest

# Avoid optional S3 dependency import path during asset_service import in tests.
if "boto3" not in sys.modules:
    boto3 = types.ModuleType("boto3")
    boto3.client = lambda *args, **kwargs: object()
    sys.modules["boto3"] = boto3
if "botocore.config" not in sys.modules:
    botocore_config = types.ModuleType("botocore.config")
    botocore_config.Config = lambda *args, **kwargs: object()
    sys.modules["botocore.config"] = botocore_config
if "botocore.exceptions" not in sys.modules:
    botocore_exceptions = types.ModuleType("botocore.exceptions")
    botocore_exceptions.ClientError = Exception
    sys.modules["botocore.exceptions"] = botocore_exceptions

from app.services import asset_service


class _FakeDB:
    def __init__(self):
        self.added = []

    async def execute(self, _stmt):
        raise AssertionError("execute should not be called in these tests")

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        return None

    async def refresh(self, _item):
        return None


class _FakeStorage:
    def __init__(self):
        self.writes = []

    async def write(self, path: str, content: bytes):
        self.writes.append((path, content))


class _DummyAsset:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@pytest.mark.asyncio
async def test_upload_rejected_when_quota_would_be_exceeded(monkeypatch):
    db = _FakeDB()
    storage = _FakeStorage()
    user = SimpleNamespace(id=uuid4(), storage_used_bytes=10, storage_quota_bytes=12)
    file = SimpleNamespace(
        filename="photo.jpg",
        content_type="image/jpeg",
        file=io.BytesIO(b"abcde"),
        seek=lambda pos: None,
        read=lambda: None,
    )

    async def _seek(pos):
        file.file.seek(pos)

    async def _read():
        return file.file.read()

    file.seek = _seek
    file.read = _read

    async def _hash(_):
        return "a" * 64

    async def _not_duplicate(*_args, **_kwargs):
        return None

    monkeypatch.setattr(asset_service, "compute_sha256_async", _hash)
    monkeypatch.setattr(asset_service, "get_asset_by_hash", _not_duplicate)

    with pytest.raises(asset_service.QuotaExceededError):
        await asset_service.create_asset(db=db, storage=storage, user=user, file=file)

    assert user.storage_used_bytes == 10
    assert storage.writes == []


@pytest.mark.asyncio
async def test_upload_succeeds_under_quota(monkeypatch):
    db = _FakeDB()
    storage = _FakeStorage()
    user = SimpleNamespace(id=uuid4(), storage_used_bytes=10, storage_quota_bytes=20)
    file = SimpleNamespace(
        filename="photo.jpg",
        content_type="image/jpeg",
        file=io.BytesIO(b"abcde"),
        seek=lambda pos: None,
        read=lambda: None,
    )

    async def _seek(pos):
        file.file.seek(pos)

    async def _read():
        return file.file.read()

    file.seek = _seek
    file.read = _read

    async def _hash(_):
        return "b" * 64

    async def _not_duplicate(*_args, **_kwargs):
        return None

    monkeypatch.setattr(asset_service, "Asset", _DummyAsset)
    monkeypatch.setattr(asset_service, "compute_sha256_async", _hash)
    monkeypatch.setattr(asset_service, "get_asset_by_hash", _not_duplicate)

    asset, is_duplicate = await asset_service.create_asset(
        db=db, storage=storage, user=user, file=file
    )

    assert isinstance(asset, _DummyAsset)
    assert is_duplicate is False
    assert user.storage_used_bytes == 15
    assert len(storage.writes) == 1


@pytest.mark.asyncio
async def test_duplicate_does_not_consume_quota_or_storage(monkeypatch):
    db = _FakeDB()
    storage = _FakeStorage()
    user = SimpleNamespace(id=uuid4(), storage_used_bytes=12, storage_quota_bytes=12)
    existing = SimpleNamespace(id=uuid4(), storage_path="originals/cc/cc/cc.jpg")
    file = SimpleNamespace(
        filename="photo.jpg",
        content_type="image/jpeg",
        file=io.BytesIO(b"abcde"),
        seek=lambda pos: None,
        read=lambda: None,
    )

    async def _hash(_):
        return "c" * 64

    async def _duplicate(*_args, **_kwargs):
        return existing

    monkeypatch.setattr(asset_service, "compute_sha256_async", _hash)
    monkeypatch.setattr(asset_service, "get_asset_by_hash", _duplicate)

    asset, is_duplicate = await asset_service.create_asset(
        db=db, storage=storage, user=user, file=file
    )

    assert asset is existing
    assert is_duplicate is True
    assert user.storage_used_bytes == 12
    assert storage.writes == []
