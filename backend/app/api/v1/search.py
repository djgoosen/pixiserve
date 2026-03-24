"""
Search API endpoints.

Supports filtering by:
- Text (filename, location)
- Date range
- People (faces)
- Tags (objects, scenes)
- Location (city, country, GPS radius)
- Asset type (image, video)
- Favorites
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models import Asset, AssetTag, Face, Tag, TagType

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str | None = None  # Text search
    asset_type: str | None = None  # "image" or "video"
    date_from: datetime | None = None
    date_to: datetime | None = None
    people_ids: list[UUID] | None = None
    tag_names: list[str] | None = None
    city: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float | None = None  # Search radius in km
    is_favorite: bool | None = None


class SearchResult(BaseModel):
    """Individual search result."""
    id: UUID
    thumb_url: str
    captured_at: datetime | None
    original_filename: str | None
    city: str | None
    country: str | None
    is_favorite: bool


class SearchResponse(BaseModel):
    """Paginated search response."""
    items: list[SearchResult]
    total: int
    facets: dict | None = None


def _is_postgres(db: AsyncSession) -> bool:
    bind = getattr(db, "bind", None)
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", None) == "postgresql"


@router.post("", response_model=SearchResponse)
async def search_assets(
    request: SearchRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """
    Search assets with various filters.

    Supports combining multiple filters with AND logic.
    """
    query = (
        select(Asset)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
    )

    # Text search (filename, city, country)
    rank_expr = None
    if request.query:
        search_term = f"%{request.query.lower()}%"
        query = query.where(
            or_(
                func.lower(Asset.original_filename).like(search_term),
                func.lower(Asset.city).like(search_term),
                func.lower(Asset.country).like(search_term),
            )
        )
        if _is_postgres(db):
            q = request.query.lower()
            rank_expr = func.greatest(
                func.similarity(func.lower(func.coalesce(Asset.original_filename, "")), q),
                func.similarity(func.lower(func.coalesce(Asset.city, "")), q),
                func.similarity(func.lower(func.coalesce(Asset.country, "")), q),
            )

    # Asset type filter
    if request.asset_type:
        query = query.where(Asset.asset_type == request.asset_type)

    # Date range filter
    if request.date_from:
        query = query.where(Asset.captured_at >= request.date_from)
    if request.date_to:
        query = query.where(Asset.captured_at <= request.date_to)

    # People filter
    if request.people_ids:
        query = (
            query
            .join(Face)
            .where(Face.person_id.in_(request.people_ids))
        )

    # Tag filter
    if request.tag_names:
        query = (
            query
            .join(AssetTag)
            .join(Tag)
            .where(Tag.name.in_(request.tag_names))
        )

    # Location filters
    if request.city:
        query = query.where(func.lower(Asset.city) == request.city.lower())

    if request.country:
        query = query.where(func.lower(Asset.country) == request.country.lower())

    # GPS radius search (approximate using bounding box)
    if request.latitude and request.longitude and request.radius_km:
        # Approximate degrees per km at equator
        lat_range = request.radius_km / 111.0
        lon_range = request.radius_km / (111.0 * abs(request.latitude) * 0.0174533 + 0.0001)

        query = query.where(
            and_(
                Asset.latitude.between(
                    request.latitude - lat_range,
                    request.latitude + lat_range
                ),
                Asset.longitude.between(
                    request.longitude - lon_range,
                    request.longitude + lon_range
                ),
            )
        )

    # Favorites filter
    if request.is_favorite is not None:
        query = query.where(Asset.is_favorite == request.is_favorite)

    # Distinct to handle joins
    query = query.distinct()

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate and order
    if rank_expr is not None:
        query = query.order_by(
            rank_expr.desc(),
            Asset.captured_at.desc().nullslast(),
            Asset.created_at.desc(),
        )
    else:
        query = query.order_by(Asset.captured_at.desc().nullslast(), Asset.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    assets = result.scalars().all()

    items = [
        SearchResult(
            id=a.id,
            thumb_url=f"/api/v1/assets/{a.id}/thumbnail",
            captured_at=a.captured_at,
            original_filename=a.original_filename,
            city=a.city,
            country=a.country,
            is_favorite=a.is_favorite,
        )
        for a in assets
    ]

    return SearchResponse(items=items, total=total)


@router.get("/suggestions")
async def get_search_suggestions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query("", min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Get search suggestions based on partial query.

    Returns matching cities, countries, tags, and people names.
    """
    search_term = f"%{q.lower()}%"
    suggestions = []

    # Cities
    cities = await db.execute(
        select(Asset.city)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.city.isnot(None))
        .where(func.lower(Asset.city).like(search_term))
        .distinct()
        .limit(5)
    )
    for row in cities:
        if row[0]:
            suggestions.append({"type": "city", "value": row[0]})

    # Countries
    countries = await db.execute(
        select(Asset.country)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.country.isnot(None))
        .where(func.lower(Asset.country).like(search_term))
        .distinct()
        .limit(5)
    )
    for row in countries:
        if row[0]:
            suggestions.append({"type": "country", "value": row[0]})

    # Tags
    tags = await db.execute(
        select(Tag.name, Tag.tag_type)
        .join(AssetTag)
        .join(Asset)
        .where(Asset.owner_id == current_user.id)
        .where(func.lower(Tag.name).like(search_term))
        .distinct()
        .limit(5)
    )
    for row in tags:
        suggestions.append({"type": row[1].value, "value": row[0]})

    # People (names)
    from app.models import Person
    people = await db.execute(
        select(Person.id, Person.name)
        .where(Person.owner_id == current_user.id)
        .where(Person.name.isnot(None))
        .where(func.lower(Person.name).like(search_term))
        .limit(5)
    )
    for row in people:
        suggestions.append({"type": "person", "value": row[1], "id": str(row[0])})

    return {"suggestions": suggestions[:limit]}


@router.get("/facets")
async def get_search_facets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get available facets for filtering.

    Returns counts for cities, countries, years, tags, and people.
    """
    facets = {}

    # Years
    years = await db.execute(
        select(
            func.extract("year", Asset.captured_at).label("year"),
            func.count().label("count"),
        )
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
        .where(Asset.captured_at.isnot(None))
        .group_by(func.extract("year", Asset.captured_at))
        .order_by(func.extract("year", Asset.captured_at).desc())
    )
    facets["years"] = [{"year": int(r[0]), "count": r[1]} for r in years if r[0]]

    # Countries
    countries = await db.execute(
        select(Asset.country, func.count().label("count"))
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
        .where(Asset.country.isnot(None))
        .group_by(Asset.country)
        .order_by(func.count().desc())
        .limit(20)
    )
    facets["countries"] = [{"name": r[0], "count": r[1]} for r in countries]

    # Cities
    cities = await db.execute(
        select(Asset.city, func.count().label("count"))
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
        .where(Asset.city.isnot(None))
        .group_by(Asset.city)
        .order_by(func.count().desc())
        .limit(20)
    )
    facets["cities"] = [{"name": r[0], "count": r[1]} for r in cities]

    # Top tags
    top_tags = await db.execute(
        select(Tag.name, Tag.tag_type, func.count().label("count"))
        .join(AssetTag)
        .join(Asset)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
        .group_by(Tag.id)
        .order_by(func.count().desc())
        .limit(30)
    )
    facets["tags"] = [
        {"name": r[0], "type": r[1].value, "count": r[2]}
        for r in top_tags
    ]

    # Asset types
    types = await db.execute(
        select(Asset.asset_type, func.count().label("count"))
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
        .group_by(Asset.asset_type)
    )
    facets["types"] = [{"type": r[0], "count": r[1]} for r in types]

    return facets
