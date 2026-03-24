import secrets
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def generate_secret_key() -> str:
    """Generate a secure random secret key."""
    return secrets.token_hex(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    # Application
    app_name: str = "Pixiserve"
    debug: bool = False
    secret_key: str = ""  # Will be generated if not provided

    # Database
    database_url: str = "postgresql+asyncpg://pixiserve:pixiserve@localhost:5432/pixiserve"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Storage
    storage_type: Literal["local", "s3"] = "local"
    storage_path: str = "/data/photos"

    # S3 (optional)
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Registration
    allow_registration: bool = True  # Set to False after creating admin

    # Clerk (session JWT verification on the API; publishable key is for frontends)
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_webhook_secret: str = ""  # Svix signing secret (whsec_...) from Clerk dashboard

    def model_post_init(self, __context) -> None:
        """Generate secret key if not provided."""
        if not self.secret_key:
            object.__setattr__(self, "secret_key", generate_secret_key())

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
