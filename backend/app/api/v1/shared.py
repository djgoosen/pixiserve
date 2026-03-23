"""Public album access via share token (no user session)."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Album, AlbumAsset, AlbumShare, Asset, ShareType
from app.services.share_link_password import SharePasswordCheck, check_share_link_password

router = APIRouter()


class SharedAlbumResponse(BaseModel):
    """Minimal album info for anonymous viewers."""

    id: UUID
    title: str
    description: str | None
    asset_count: int

    model_config = {"from_attributes": True}


def _raise_for_password_result(result: SharePasswordCheck) -> None:
    if result == SharePasswordCheck.REQUIRED_MISSING:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="password_required",
        )
    if result == SharePasswordCheck.INVALID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_password",
        )


async def _get_link_share_or_404(
    db: AsyncSession,
    share_token: str,
) -> tuple[AlbumShare, Album]:
    result = await db.execute(
        select(AlbumShare, Album)
        .join(Album, AlbumShare.album_id == Album.id)
        .where(
            AlbumShare.share_token == share_token,
            AlbumShare.share_type == ShareType.LINK,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")
    share, album = row
    now = datetime.now(timezone.utc)
    if share.expires_at is not None and share.expires_at < now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share expired")
    return share, album


@router.get("/{share_token}", response_model=SharedAlbumResponse)
async def get_shared_album(
    share_token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_share_password: Annotated[str | None, Header(alias="X-Share-Password")] = None,
):
    """Return album metadata for a valid share link; use X-Share-Password when the link is protected."""
    share, album = await _get_link_share_or_404(db, share_token)
    pw = await check_share_link_password(db, share, x_share_password)
    if pw not in (SharePasswordCheck.OK, SharePasswordCheck.NOT_REQUIRED):
        _raise_for_password_result(pw)

    share.view_count += 1
    share.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()

    return SharedAlbumResponse.model_validate(album)


@router.get("/{share_token}/assets")
async def get_shared_album_assets(
    share_token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_share_password: Annotated[str | None, Header(alias="X-Share-Password")] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List assets visible through a share link (same password rules as GET /shared/{token})."""
    share, album = await _get_link_share_or_404(db, share_token)
    pw = await check_share_link_password(db, share, x_share_password)
    if pw not in (SharePasswordCheck.OK, SharePasswordCheck.NOT_REQUIRED):
        _raise_for_password_result(pw)

    query = (
        select(Asset)
        .join(AlbumAsset)
        .where(AlbumAsset.album_id == album.id)
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
