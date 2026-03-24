from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_clerk_user_id
from app.services.clerk_jwt import ClerkJWTError, verify_clerk_session_token

security = HTTPBearer()
optional_bearer = HTTPBearer(auto_error=False)


async def _user_from_clerk_session_token(db: AsyncSession, token: str) -> User:
    try:
        claims = verify_clerk_session_token(token)
    except ClerkJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    clerk_user_id = claims["sub"]
    user = await get_user_by_clerk_user_id(db, clerk_user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    return await _user_from_clerk_session_token(db, credentials.credentials)


async def get_current_user_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(optional_bearer),
    ],
    token: Annotated[
        str | None,
        Query(
            None,
            description="Clerk session JWT for <img>/<video> src (no Authorization header).",
        ),
    ],
) -> User:
    raw = (token or "").strip() or (credentials.credentials if credentials else None) or ""
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _user_from_clerk_session_token(db, raw)


CurrentUser = Annotated[User, Depends(get_current_user)]
MediaUser = Annotated[User, Depends(get_current_user_media)]
