from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.api.deps import CurrentUser
from app.schemas.auth import (
    LoginResponse,
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    change_password,
    create_access_token,
    create_user,
    get_user_by_email,
    get_user_by_username,
    get_user_count,
)

router = APIRouter()

_LOCAL_AUTH_DISABLED_DETAIL = (
    "Local username/password authentication is disabled. Sign in with Clerk and send "
    "the Clerk session JWT as Bearer token. For development or migration only, set "
    "ALLOW_LOCAL_PASSWORD_AUTH=true (not for production)."
)


def _require_local_password_auth() -> None:
    if not get_settings().allow_local_password_auth:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_LOCAL_AUTH_DISABLED_DETAIL,
        )


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user account."""
    _require_local_password_auth()
    settings = get_settings()
    # Check if registration is allowed
    if not settings.allow_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )

    # Check if username exists
    existing = await get_user_by_username(db, user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Check if email exists
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # First user becomes admin
    user_count = await get_user_count(db)
    is_admin = user_count == 0

    user = await create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
        is_admin=is_admin,
    )

    access_token, expires_in = create_access_token(user.id)

    return LoginResponse(
        user=UserResponse.model_validate(user),
        token=TokenResponse(
            access_token=access_token,
            expires_in=expires_in,
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with username/email and password."""
    _require_local_password_auth()
    user = await authenticate_user(db, credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token, expires_in = create_access_token(user.id)

    return LoginResponse(
        user=UserResponse.model_validate(user),
        token=TokenResponse(
            access_token=access_token,
            expires_in=expires_in,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_user_password(
    password_data: PasswordChange,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change the locally stored password hash (only when local password auth is enabled)."""
    _require_local_password_auth()
    success = await change_password(
        db=db,
        user=current_user,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(current_user: CurrentUser):
    """Logout (client should discard token)."""
    return {"message": "Successfully logged out"}
