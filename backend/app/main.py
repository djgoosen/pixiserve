from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.clerk_secret_key.strip():
        raise RuntimeError(
            "CLERK_SECRET_KEY is required. Set it in the environment (see README and deploy/.env.example)."
        )
    if not settings.clerk_publishable_key.strip():
        raise RuntimeError(
            "CLERK_PUBLISHABLE_KEY is required for documented deploys "
            "(used by web/mobile Clerk SDKs; the API validates session JWTs via JWKS)."
        )
    if not settings.clerk_webhook_secret.strip():
        raise RuntimeError(
            "CLERK_WEBHOOK_SECRET is required for Svix-signed Clerk webhooks "
            "(see README and deploy/.env.example)."
        )
    yield
    # Shutdown
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
