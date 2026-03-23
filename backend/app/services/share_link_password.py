"""Album share link password hashing and verification (bcrypt).

New shares store ``AlbumShare.link_password`` as a bcrypt hash (via ``hash_password``).

**Legacy plaintext:** Rows created before this change may still hold plaintext. On the
first successful ``X-Share-Password`` match, the value is replaced with a bcrypt hash
(``check_share_link_password`` flushes the session; the API route commits). No separate
batch migration is required for correctness; optional SQL to find legacy rows:
``SELECT id FROM album_shares WHERE link_password IS NOT NULL AND link_password NOT LIKE '$2%'``.
"""

import secrets
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.album import AlbumShare
from app.services.auth_service import hash_password, verify_password

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def is_bcrypt_password_hash(stored: str) -> bool:
    """Return True if ``stored`` looks like a bcrypt hash."""
    return stored.startswith(_BCRYPT_PREFIXES)


def hash_link_password(plain: str | None) -> str | None:
    """Return a bcrypt hash for a share password, or None when unset."""
    if plain is None or plain == "":
        return None
    return hash_password(plain)


class SharePasswordCheck(str, Enum):
    OK = "ok"
    NOT_REQUIRED = "not_required"
    REQUIRED_MISSING = "required_missing"
    INVALID = "invalid"


async def check_share_link_password(
    db: AsyncSession,
    share: AlbumShare,
    provided_password: str | None,
) -> SharePasswordCheck:
    """
    Validate optional share password.

    Legacy plaintext values in ``share.link_password`` are verified with a
    timing-safe compare; on success the field is re-hashed to bcrypt and flushed.
    """
    stored = share.link_password
    if not stored:
        return SharePasswordCheck.NOT_REQUIRED

    if provided_password is None or provided_password == "":
        return SharePasswordCheck.REQUIRED_MISSING

    if is_bcrypt_password_hash(stored):
        if verify_password(provided_password, stored):
            return SharePasswordCheck.OK
        return SharePasswordCheck.INVALID

    if secrets.compare_digest(stored, provided_password):
        share.link_password = hash_password(provided_password)
        await db.flush()
        return SharePasswordCheck.OK
    return SharePasswordCheck.INVALID
