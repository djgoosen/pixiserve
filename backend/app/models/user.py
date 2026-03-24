from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.album import Album
    from app.models.device import Device
    from app.models.face import Person


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    # Authentication
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    clerk_user_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Profile
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # App-specific fields
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    storage_quota_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="owner")
    albums: Mapped[list["Album"]] = relationship("Album", back_populates="owner")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="owner")
    people: Mapped[list["Person"]] = relationship("Person", back_populates="owner")

    def __repr__(self) -> str:
        return f"<User {self.username}>"
