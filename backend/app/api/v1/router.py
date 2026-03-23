from fastapi import APIRouter

from app.api.v1 import auth, assets, health, system, people, sync, albums, search, shared

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(people.router, prefix="/people", tags=["people"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(albums.router, prefix="/albums", tags=["albums"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(shared.router, prefix="/shared", tags=["shared"])
