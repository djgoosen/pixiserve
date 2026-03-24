import mimetypes
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.user import User
from app.storage import StorageBackend
from app.utils.hashing import compute_sha256_async


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/avif",
    "image/tiff",
    "image/bmp",
}

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "video/mpeg",
}

ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


class QuotaExceededError(ValueError):
    """Raised when an upload would exceed a user's configured storage quota."""


def get_asset_type(mime_type: str) -> str:
    if mime_type in ALLOWED_IMAGE_TYPES:
        return "image"
    if mime_type in ALLOWED_VIDEO_TYPES:
        return "video"
    return "unknown"


def generate_storage_path(file_hash: str, filename: str | None) -> str:
    """Generate a storage path based on hash for even distribution."""
    ext = ""
    if filename:
        ext = Path(filename).suffix.lower()

    # Use first 4 chars of hash for directory structure: ab/cd/abcdef...
    dir1 = file_hash[:2]
    dir2 = file_hash[2:4]

    return f"originals/{dir1}/{dir2}/{file_hash}{ext}"


async def get_asset_by_hash(
    db: AsyncSession,
    user_id: UUID,
    file_hash: str,
) -> Asset | None:
    stmt = select(Asset).where(
        Asset.owner_id == user_id,
        Asset.file_hash_sha256 == file_hash,
        Asset.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_asset(
    db: AsyncSession,
    storage: StorageBackend,
    user: User,
    file: UploadFile,
) -> tuple[Asset, bool]:
    """
    Upload a file and create an asset record.
    Returns (asset, is_duplicate).
    """
    # Validate mime type
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0]
    if mime_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported file type: {mime_type}")

    # Compute hash
    file_hash = await compute_sha256_async(file.file)

    # Check for duplicate
    existing = await get_asset_by_hash(db, user.id, file_hash)
    if existing:
        return existing, True

    # Generate storage path and upload
    storage_path = generate_storage_path(file_hash, file.filename)

    await file.seek(0)
    content = await file.read()
    content_size = len(content)

    # Null/zero quota means unlimited storage. Enforce only positive quotas.
    quota = user.storage_quota_bytes
    if quota and quota > 0:
        projected_usage = user.storage_used_bytes + content_size
        if projected_usage > quota:
            raise QuotaExceededError(
                f"Storage quota exceeded: {user.storage_used_bytes}/{quota} bytes used"
            )

    await storage.write(storage_path, content)

    # Create asset record
    asset = Asset(
        owner_id=user.id,
        file_hash_sha256=file_hash,
        original_filename=file.filename,
        storage_path=storage_path,
        file_size_bytes=content_size,
        mime_type=mime_type,
        asset_type=get_asset_type(mime_type),
    )

    db.add(asset)

    # Update user's storage usage
    user.storage_used_bytes += content_size

    await db.commit()
    await db.refresh(asset)

    return asset, False


async def get_assets(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 50,
    asset_type: str | None = None,
    is_favorite: bool | None = None,
) -> tuple[list[Asset], int]:
    """Get paginated assets for a user."""
    stmt = select(Asset).where(
        Asset.owner_id == user_id,
        Asset.deleted_at.is_(None),
    )

    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)

    if is_favorite is not None:
        stmt = stmt.where(Asset.is_favorite == is_favorite)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order
    stmt = stmt.order_by(Asset.captured_at.desc().nulls_last(), Asset.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    assets = list(result.scalars().all())

    return assets, total


async def get_asset_by_id(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID,
) -> Asset | None:
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.owner_id == user_id,
        Asset.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_asset(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID,
) -> bool:
    """Soft delete an asset."""
    asset = await get_asset_by_id(db, user_id, asset_id)
    if not asset:
        return False

    asset.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def toggle_favorite(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID,
) -> Asset | None:
    """Toggle favorite status on an asset."""
    asset = await get_asset_by_id(db, user_id, asset_id)
    if not asset:
        return None

    asset.is_favorite = not asset.is_favorite
    await db.commit()
    await db.refresh(asset)
    return asset
