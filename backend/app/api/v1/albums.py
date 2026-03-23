"""
Albums API endpoints.

Supports standard albums, smart albums, and sharing.
"""

import secrets
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models import Album, AlbumAsset, AlbumShare, AlbumType, ShareType, Asset
from app.services.share_link_password import hash_link_password

router = APIRouter()


class AlbumCreate(BaseModel):
    """Album creation request."""

    title: str
    description: str | None = None
    album_type: AlbumType = AlbumType.STANDARD
    smart_criteria: dict | None = None  # For smart albums


class AlbumUpdate(BaseModel):
    """Album update request."""

    title: str | None = None
    description: str | None = None
    cover_asset_id: UUID | None = None
    smart_criteria: dict | None = None


class AlbumResponse(BaseModel):
    """Album response model."""

    id: UUID
    title: str
    description: str | None
    album_type: AlbumType
    cover_asset_id: UUID | None
    asset_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlbumListResponse(BaseModel):
    """Paginated album list."""

    items: list[AlbumResponse]
    total: int


class AddAssetsRequest(BaseModel):
    """Request to add assets to album."""

    asset_ids: list[UUID]


class ShareLinkCreate(BaseModel):
    """Create share link request."""

    password: str | None = None
    expires_at: datetime | None = None
    can_download: bool = True

    @field_validator("password", mode="before")
    @classmethod
    def empty_password_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v


class ShareLinkResponse(BaseModel):
    """Share link response."""

    id: UUID
    share_token: str
    share_url: str
    expires_at: datetime | None
    can_download: bool
    view_count: int
    has_password: bool = False


@router.post("", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    request: AlbumCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new album."""
    album = Album(
        owner_id=current_user.id,
        title=request.title,
        description=request.description,
        album_type=request.album_type,
        smart_criteria=request.smart_criteria,
    )
    db.add(album)
    await db.commit()
    await db.refresh(album)

    return AlbumResponse.model_validate(album)


@router.get("", response_model=AlbumListResponse)
async def list_albums(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    album_type: AlbumType | None = None,
):
    """List albums for the current user."""
    query = select(Album).where(Album.owner_id == current_user.id)

    if album_type:
        query = query.where(Album.album_type == album_type)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = (
        query.order_by(Album.sort_order.asc(), Album.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    albums = result.scalars().all()

    return AlbumListResponse(
        items=[AlbumResponse.model_validate(a) for a in albums],
        total=total,
    )


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    return AlbumResponse.model_validate(album)


@router.patch("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: UUID,
    update: AlbumUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    if update.title is not None:
        album.title = update.title
    if update.description is not None:
        album.description = update.description
    if update.cover_asset_id is not None:
        album.cover_asset_id = update.cover_asset_id
    if update.smart_criteria is not None:
        album.smart_criteria = update.smart_criteria

    await db.commit()
    await db.refresh(album)

    return AlbumResponse.model_validate(album)


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an album (does not delete assets)."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    await db.delete(album)
    await db.commit()


@router.get("/{album_id}/assets")
async def get_album_assets(
    album_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get assets in an album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    if album.album_type == AlbumType.SMART and album.smart_criteria:
        # Smart album - execute criteria query
        return await _get_smart_album_assets(
            db, current_user.id, album.smart_criteria, page, page_size
        )

    # Standard album
    query = (
        select(Asset)
        .join(AlbumAsset)
        .where(AlbumAsset.album_id == album_id)
        .order_by(AlbumAsset.position.asc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    assets = result.scalars().all()

    return {
        "items": [
            {
                "id": str(a.id),
                "thumb_url": f"/api/v1/assets/{a.id}/thumbnail",
                "captured_at": a.captured_at.isoformat() if a.captured_at else None,
            }
            for a in assets
        ],
        "total": total,
    }


async def _get_smart_album_assets(
    db: AsyncSession,
    owner_id: UUID,
    criteria: dict,
    page: int,
    page_size: int,
):
    """Execute smart album criteria query."""
    from app.models import AssetTag, Face

    query = select(Asset).where(Asset.owner_id == owner_id).where(Asset.deleted_at.is_(None))

    # Filter by people
    if "people" in criteria and criteria["people"]:
        query = query.join(Face).where(Face.person_id.in_(criteria["people"]))

    # Filter by tags
    if "tags" in criteria and criteria["tags"]:
        query = query.join(AssetTag).where(AssetTag.tag_id.in_(criteria["tags"]))

    # Filter by date range
    if "date_range" in criteria and len(criteria["date_range"]) == 2:
        start, end = criteria["date_range"]
        if start:
            query = query.where(Asset.captured_at >= start)
        if end:
            query = query.where(Asset.captured_at <= end)

    # Filter by location
    if "city" in criteria and criteria["city"]:
        query = query.where(Asset.city == criteria["city"])

    if "country" in criteria and criteria["country"]:
        query = query.where(Asset.country == criteria["country"])

    query = query.distinct()

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Asset.captured_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    assets = result.scalars().all()

    return {
        "items": [
            {
                "id": str(a.id),
                "thumb_url": f"/api/v1/assets/{a.id}/thumbnail",
                "captured_at": a.captured_at.isoformat() if a.captured_at else None,
            }
            for a in assets
        ],
        "total": total,
    }


@router.post("/{album_id}/assets")
async def add_assets_to_album(
    album_id: UUID,
    request: AddAssetsRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add assets to an album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    if album.album_type == AlbumType.SMART:
        raise HTTPException(status_code=400, detail="Cannot manually add to smart albums")

    # Get max position
    max_pos = (
        await db.scalar(
            select(func.max(AlbumAsset.position)).where(AlbumAsset.album_id == album_id)
        )
        or 0
    )

    added = 0
    for i, asset_id in enumerate(request.asset_ids):
        # Verify asset ownership
        asset = await db.get(Asset, asset_id)
        if not asset or asset.owner_id != current_user.id:
            continue

        # Check if already in album
        existing = await db.execute(
            select(AlbumAsset).where(
                AlbumAsset.album_id == album_id,
                AlbumAsset.asset_id == asset_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        album_asset = AlbumAsset(
            album_id=album_id,
            asset_id=asset_id,
            position=max_pos + i + 1,
            added_by_id=current_user.id,
        )
        db.add(album_asset)
        added += 1

    album.asset_count += added

    # Set cover if not set
    if not album.cover_asset_id and request.asset_ids:
        album.cover_asset_id = request.asset_ids[0]

    await db.commit()

    return {"added": added}


@router.delete("/{album_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_asset_from_album(
    album_id: UUID,
    asset_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove an asset from an album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    result = await db.execute(
        select(AlbumAsset).where(
            AlbumAsset.album_id == album_id,
            AlbumAsset.asset_id == asset_id,
        )
    )
    album_asset = result.scalar_one_or_none()

    if album_asset:
        await db.delete(album_asset)
        album.asset_count = max(0, album.asset_count - 1)
        await db.commit()


@router.post("/{album_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    album_id: UUID,
    request: ShareLinkCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a public share link for an album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    # Generate share token
    share_token = secrets.token_urlsafe(32)

    share = AlbumShare(
        album_id=album_id,
        share_type=ShareType.LINK,
        share_token=share_token,
        link_password=hash_link_password(request.password),
        expires_at=request.expires_at,
        can_download=request.can_download,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return ShareLinkResponse(
        id=share.id,
        share_token=share_token,
        share_url=f"/shared/{share_token}",
        expires_at=share.expires_at,
        can_download=share.can_download,
        view_count=share.view_count,
        has_password=share.link_password is not None,
    )


@router.get("/{album_id}/shares", response_model=list[ShareLinkResponse])
async def list_album_shares(
    album_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all shares for an album."""
    album = await db.get(Album, album_id)

    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Album not found")

    result = await db.execute(
        select(AlbumShare)
        .where(AlbumShare.album_id == album_id)
        .where(AlbumShare.share_type == ShareType.LINK)
    )
    shares = result.scalars().all()

    return [
        ShareLinkResponse(
            id=s.id,
            share_token=s.share_token,
            share_url=f"/shared/{s.share_token}",
            expires_at=s.expires_at,
            can_download=s.can_download,
            view_count=s.view_count,
            has_password=s.link_password is not None,
        )
        for s in shares
    ]


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share(
    share_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a share link."""
    share = await db.get(AlbumShare, share_id)

    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    album = await db.get(Album, share.album_id)
    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Share not found")

    await db.delete(share)
    await db.commit()
