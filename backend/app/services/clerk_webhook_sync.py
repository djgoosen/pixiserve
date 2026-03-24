"""Apply Clerk `user.*` webhook payloads to local users (idempotent upsert).

FR-AUTH-02 (first admin): the first **local** ``User`` row created from Clerk data
(when ``get_user_count()`` is ``0`` immediately before insert) receives ``is_admin=True``.
Every later insert gets ``is_admin=False``. This matches a homelab pattern where the
first person to hit Clerk sign-up becomes the Pixiserve admin; it is deterministic
and independent of Clerk dashboard role APIs.
"""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import (
    get_user_by_clerk_user_id,
    get_user_by_username,
    get_user_count,
    hash_password,
)


def extract_primary_email(user_data: dict[str, Any]) -> str:
    emails = user_data.get("email_addresses") or []
    primary_id = user_data.get("primary_email_address_id")
    for e in emails:
        if primary_id and e.get("id") == primary_id:
            addr = e.get("email_address")
            if addr:
                return str(addr)[:255]
    for e in emails:
        addr = e.get("email_address")
        if addr:
            return str(addr)[:255]
    clerk_id = user_data.get("id", "unknown")
    return f"noreply+{clerk_id}@clerk.placeholder.invalid"[:255]


def extract_display_name(user_data: dict[str, Any]) -> str | None:
    parts = [user_data.get("first_name"), user_data.get("last_name")]
    parts = [p for p in parts if p]
    if parts:
        return " ".join(str(p) for p in parts)[:255]
    return None


def derive_username_base(user_data: dict[str, Any], email: str, clerk_id: str) -> str:
    un = user_data.get("username")
    if un:
        return str(un)[:50]
    if "@" in email and not email.endswith("@clerk.placeholder.invalid"):
        return email.split("@", 1)[0][:50] or "user"
    return f"user_{clerk_id[-12:]}"[:50]


async def allocate_unique_username(db: AsyncSession, base: str) -> str:
    base = (base or "user")[:50]
    candidate = base
    n = 0
    while True:
        existing = await get_user_by_username(db, candidate)
        if not existing:
            return candidate
        n += 1
        suffix = f"_{n}"
        candidate = (base[: 50 - len(suffix)] + suffix)[:50]


async def upsert_user_from_clerk_data(db: AsyncSession, user_data: dict[str, Any]) -> User:
    """
    Create or update a local user from a Clerk user object (`data` on user.* events).
    Idempotent on `clerk_user_id`.
    """
    clerk_id = user_data.get("id")
    if not clerk_id or not isinstance(clerk_id, str):
        raise ValueError("clerk user id missing")

    email = extract_primary_email(user_data)
    name = extract_display_name(user_data)
    username_base = derive_username_base(user_data, email, clerk_id)

    existing = await get_user_by_clerk_user_id(db, clerk_id)
    if existing:
        existing.email = email
        existing.name = name
        await db.commit()
        await db.refresh(existing)
        return existing

    username = await allocate_unique_username(db, username_base)
    # FR-AUTH-02: only the first row in `users` at insert time is admin (see module docstring).
    count = await get_user_count(db)
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        clerk_user_id=clerk_id,
        name=name,
        is_admin=count == 0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
