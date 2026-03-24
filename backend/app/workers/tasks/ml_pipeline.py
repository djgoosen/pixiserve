"""
ML processing pipeline task.

Orchestrates all ML processing for an asset:
1. Generate thumbnails
2. Extract EXIF metadata
3. Reverse geocode (if GPS available)
4. Face detection (Phase 4)
5. Object detection (Phase 4)
6. Scene classification (Phase 4)
"""

import logging
from datetime import datetime, timezone

from celery import chain, chord, group, shared_task

from app.workers.tasks.thumbnails import generate_thumbnails, generate_video_thumbnail
from app.workers.tasks.exif import extract_exif, extract_video_metadata
from app.workers.tasks.geocoding import reverse_geocode

logger = logging.getLogger(__name__)


def apply_processing_results_to_asset(asset, processing_results: dict) -> None:
    """
    Apply extracted metadata/thumbnail results to an asset object.

    Designed to be deterministic and idempotent so retries do not corrupt fields.
    """
    exif = processing_results.get("exif", {})
    if exif.get("captured_at"):
        try:
            asset.captured_at = datetime.fromisoformat(exif["captured_at"])
        except ValueError:
            pass

    if exif.get("latitude"):
        asset.latitude = exif["latitude"]
    if exif.get("longitude"):
        asset.longitude = exif["longitude"]
    if exif.get("width"):
        asset.width = exif["width"]
    if exif.get("height"):
        asset.height = exif["height"]
    if exif.get("duration_seconds"):
        asset.duration_seconds = exif["duration_seconds"]

    # Store raw EXIF
    if exif.get("raw"):
        asset.exif_data = exif["raw"]

    # Update thumbnail paths
    thumbnails = processing_results.get("thumbnails", {})
    if thumbnails.get("thumb"):
        asset.thumb_path = thumbnails["thumb"]
    if thumbnails.get("preview"):
        asset.preview_path = thumbnails["preview"]

    # Update dimensions from thumbnail generation if not from EXIF
    if not asset.width and processing_results.get("original_size"):
        asset.width, asset.height = processing_results["original_size"]


@shared_task(bind=True)
def process_asset(
    self,
    asset_id: str,
    storage_path: str,
    asset_type: str,
    owner_id: str,
) -> dict:
    """
    Main entry point for asset processing.

    Queues all necessary processing tasks for an asset.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the original file
        asset_type: 'image' or 'video'
        owner_id: UUID of the asset owner

    Returns:
        Dictionary with task IDs for tracking
    """
    logger.info(f"Starting ML pipeline for asset {asset_id} (type: {asset_type})")

    task_ids = {}

    try:
        if asset_type == "video":
            # Video processing chain:
            # 1. Extract metadata and generate thumbnails in parallel
            # 2. Merge results
            # 3. Update asset record
            workflow = chain(
                group(
                    extract_video_metadata.s(asset_id, storage_path),
                    generate_video_thumbnail.s(asset_id, storage_path),
                ),
                process_extraction_results.s(asset_id),
                update_asset_metadata.s(asset_id),
            )
        else:
            # Image processing chain
            # 1. Extract EXIF (may contain GPS)
            # 2. Generate thumbnails (in parallel with EXIF)
            # 3. Geocode if GPS found
            # 4. Update asset record

            workflow = chain(
                # First, extract EXIF and generate thumbnails in parallel
                group(
                    extract_exif.s(asset_id, storage_path),
                    generate_thumbnails.s(asset_id, storage_path),
                ),
                # Then process results and geocode if needed
                process_extraction_results.s(asset_id),
                # Finally update the asset
                update_asset_metadata.s(asset_id),
            )

        result = workflow.apply_async()
        task_ids["pipeline"] = result.id

        logger.info(f"ML pipeline queued for {asset_id}: {result.id}")

    except Exception as e:
        logger.error(f"Failed to queue ML pipeline for {asset_id}: {e}")
        task_ids["error"] = str(e)

    return {
        "asset_id": asset_id,
        "task_ids": task_ids,
    }


@shared_task
def process_extraction_results(results: list, asset_id: str) -> dict:
    """
    Process EXIF and thumbnail results, queue geocoding if needed.

    Args:
        results: List containing [exif_result, thumbnail_result]
        asset_id: UUID of the asset

    Returns:
        Combined metadata dictionary
    """
    logger.debug(f"Processing extraction results for {asset_id}")

    combined = {
        "asset_id": asset_id,
        "exif": {},
        "thumbnails": {},
        "geocoding": None,
    }

    for result in results:
        if not result:
            continue

        if "metadata" in result:
            # EXIF result
            combined["exif"] = result.get("metadata", {})
        elif "thumbnails" in result:
            # Thumbnail result
            combined["thumbnails"] = result.get("thumbnails", {})
            if "original_size" in result:
                combined["original_size"] = result["original_size"]

    # Queue geocoding if GPS coordinates found
    exif = combined.get("exif", {})
    if exif.get("latitude") and exif.get("longitude"):
        logger.info(f"Queueing geocoding for {asset_id}")
        try:
            geo_result = reverse_geocode.delay(
                asset_id,
                exif["latitude"],
                exif["longitude"],
            )
            combined["geocoding_task_id"] = geo_result.id
        except Exception as e:
            logger.error(f"Failed to queue geocoding: {e}")

    return combined


@shared_task
def update_asset_metadata(processing_results: dict, asset_id: str) -> dict:
    """
    Update asset record with processing results.

    This task runs synchronously with the database to update
    the asset with all extracted metadata.

    Args:
        processing_results: Combined results from processing
        asset_id: UUID of the asset

    Returns:
        Status dictionary
    """
    logger.info(f"Updating asset metadata for {asset_id}")

    # Note: This requires database access
    # In production, this should use a sync DB session or
    # make an API call to update the asset

    try:
        from app.database import get_sync_session
        from app.models.asset import Asset
        from sqlalchemy import select

        with get_sync_session() as session:
            asset = session.execute(
                select(Asset).where(Asset.id == asset_id)
            ).scalar_one_or_none()

            if not asset:
                logger.error(f"Asset {asset_id} not found")
                return {"error": "Asset not found"}

            apply_processing_results_to_asset(asset, processing_results)

            # Mark ML processing complete
            asset.ml_processed_at = datetime.now(timezone.utc)

            session.commit()
            logger.info(f"Asset {asset_id} metadata updated")

            return {
                "asset_id": asset_id,
                "updated": True,
            }

    except ImportError:
        # Database module not available (running standalone)
        logger.warning("Database module not available, skipping update")
        return {
            "asset_id": asset_id,
            "updated": False,
            "reason": "Database not available",
        }
    except Exception as e:
        logger.error(f"Failed to update asset {asset_id}: {e}")
        return {
            "asset_id": asset_id,
            "updated": False,
            "error": str(e),
        }


@shared_task
def reprocess_asset(asset_id: str) -> dict:
    """
    Re-run ML pipeline for an existing asset.

    Useful for re-processing after ML model updates.

    Args:
        asset_id: UUID of the asset

    Returns:
        Task info dictionary
    """
    logger.info(f"Re-processing asset {asset_id}")

    try:
        from app.database import get_sync_session
        from app.models.asset import Asset
        from sqlalchemy import select

        with get_sync_session() as session:
            asset = session.execute(
                select(Asset).where(Asset.id == asset_id)
            ).scalar_one_or_none()

            if not asset:
                return {"error": "Asset not found"}

            # Queue processing
            return process_asset.delay(
                str(asset.id),
                asset.storage_path,
                asset.asset_type,
                str(asset.owner_id),
            ).id

    except Exception as e:
        logger.error(f"Failed to reprocess asset {asset_id}: {e}")
        return {"error": str(e)}
