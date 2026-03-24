import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, MediaUser
from app.database import get_db
from app.schemas.asset import AssetListResponse, AssetResponse, AssetUploadResponse
from app.services import asset_service
from app.storage import get_storage
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)
router = APIRouter()


def get_storage_dep() -> StorageBackend:
    return get_storage()


@router.post("", response_model=AssetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: Annotated[UploadFile, File(...)],
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage_dep)],
):
    """Upload a photo or video."""
    try:
        asset, is_duplicate = await asset_service.create_asset(
            db=db,
            storage=storage,
            user=current_user,
            file=file,
        )
    except ValueError as e:
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        if not isinstance(e, asset_service.QuotaExceededError):
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=str(e),
        )

    # Queue ML processing (non-blocking)
    if not is_duplicate:
        try:
            from app.workers.tasks.ml_pipeline import process_asset
            process_asset.delay(
                str(asset.id),
                asset.storage_path,
                asset.asset_type,
                str(current_user.id),
            )
            logger.info(f"Queued ML processing for asset {asset.id}")
        except Exception as e:
            # Don't fail the upload if ML queue fails
            logger.warning(f"Failed to queue ML processing: {e}")

    return AssetUploadResponse(
        asset=AssetResponse.model_validate(asset),
        is_duplicate=is_duplicate,
    )


@router.get("", response_model=AssetListResponse)
async def list_assets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    asset_type: str | None = Query(None, regex="^(image|video)$"),
    is_favorite: bool | None = None,
):
    """List assets for the current user."""
    assets, total = await asset_service.get_assets(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        asset_type=asset_type,
        is_favorite=is_favorite,
    )

    return AssetListResponse(
        items=[AssetResponse.model_validate(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific asset."""
    asset = await asset_service.get_asset_by_id(db, current_user.id, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    return AssetResponse.model_validate(asset)


@router.get("/{asset_id}/file")
async def get_asset_file(
    asset_id: UUID,
    current_user: MediaUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage_dep)],
):
    """Stream the original file (Bearer or ``token`` query for media elements)."""
    asset = await asset_service.get_asset_by_id(db, current_user.id, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    async def stream():
        async for chunk in storage.read_stream(asset.storage_path):
            yield chunk

    return StreamingResponse(
        stream(),
        media_type=asset.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{asset.original_filename or asset.id}"',
        },
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Soft delete an asset."""
    deleted = await asset_service.delete_asset(db, current_user.id, asset_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )


@router.post("/{asset_id}/favorite", response_model=AssetResponse)
async def toggle_favorite(
    asset_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Toggle favorite status on an asset."""
    asset = await asset_service.toggle_favorite(db, current_user.id, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    return AssetResponse.model_validate(asset)
