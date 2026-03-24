from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get user by username."""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username_or_email(db: AsyncSession, identifier: str) -> User | None:
    """Get user by username or email."""
    stmt = select(User).where(
        or_(User.username == identifier, User.email == identifier)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    name: str | None = None,
    is_admin: bool = False,
) -> User:
    """Create a new user."""
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        name=name,
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    """Authenticate a user by username/email and password."""
    user = await get_user_by_username_or_email(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return user


def create_access_token(user_id: UUID) -> tuple[str, int]:
    """Create a JWT access token."""
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> UUID | None:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return UUID(user_id)
    except JWTError:
        return None


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_clerk_user_id(db: AsyncSession, clerk_user_id: str) -> User | None:
    """Get user by Clerk user id (`sub` on Clerk session JWT)."""
    stmt = select(User).where(User.clerk_user_id == clerk_user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:
    """Change user's password. Returns True if successful."""
    if not verify_password(current_password, user.hashed_password):
        return False

    user.hashed_password = hash_password(new_password)
    await db.commit()
    return True


async def get_user_count(db: AsyncSession) -> int:
    """Get total number of users."""
    stmt = select(User)
    result = await db.execute(stmt)
    return len(result.scalars().all())
