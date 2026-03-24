"""Verify Clerk session JWTs using Clerk-hosted JWKS (RS256)."""

from __future__ import annotations

import threading
import time
from typing import Any

import jwt
from jwt import PyJWKClient

_jwks_lock = threading.Lock()
_jwks_clients: dict[str, tuple[PyJWKClient, float]] = {}
JWKS_CLIENT_TTL_SEC = 3600


class ClerkJWTError(Exception):
    """Invalid or unverifiable Clerk session token."""


def _jwks_url(issuer: str) -> str:
    return f"{issuer.rstrip('/')}/.well-known/jwks.json"


def get_jwks_client(issuer: str) -> PyJWKClient:
    """Return a cached PyJWKClient for the given Clerk issuer (`iss` claim)."""
    now = time.monotonic()
    with _jwks_lock:
        hit = _jwks_clients.get(issuer)
        if hit is not None:
            client, expires = hit
            if now < expires:
                return client
        client = PyJWKClient(_jwks_url(issuer))
        _jwks_clients[issuer] = (client, now + JWKS_CLIENT_TTL_SEC)
        return client


def verify_clerk_session_token(token: str) -> dict[str, Any]:
    """
    Validate a Clerk session JWT and return claims.

    Uses the token's `iss` claim to load `{iss}/.well-known/jwks.json` per Clerk's
    manual JWT verification flow.
    """
    if not token or not token.strip():
        raise ClerkJWTError("missing token")
    try:
        unverified = jwt.decode(
            token,
            algorithms=["RS256"],
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_nbf": False,
            },
        )
    except jwt.exceptions.DecodeError as e:
        raise ClerkJWTError(str(e)) from e
    issuer = unverified.get("iss")
    if not issuer or not isinstance(issuer, str):
        raise ClerkJWTError("missing iss")
    try:
        jwks_client = get_jwks_client(issuer)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
        )
    except jwt.exceptions.PyJWTError as e:
        raise ClerkJWTError(str(e)) from e
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise ClerkJWTError("missing sub")
    return payload
