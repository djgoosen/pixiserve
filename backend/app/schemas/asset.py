from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: UUID
    owner_id: UUID
    file_hash_sha256: str
    original_filename: str | None
    storage_path: str
    thumb_path: str | None
    preview_path: str | None
    file_size_bytes: int
    mime_type: str
    asset_type: str
    width: int | None
    height: int | None
    captured_at: datetime | None
    latitude: float | None
    longitude: float | None
    city: str | None
    country: str | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetUploadResponse(BaseModel):
    asset: AssetResponse
    is_duplicate: bool


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
