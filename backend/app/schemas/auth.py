from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str | None = None


class UserLogin(BaseModel):
    username: str  # Can be username or email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    name: str | None
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    user: UserResponse
    token: TokenResponse


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
