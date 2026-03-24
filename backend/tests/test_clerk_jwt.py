"""Clerk session JWT verification (RS256 + JWKS)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.clerk_jwt import ClerkJWTError, verify_clerk_session_token


def _rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _encode_clerk_like_token(private_key, *, issuer: str, sub: str = "user_2abc", **extra):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iss": issuer,
        "iat": now,
        "exp": now + timedelta(hours=1),
        **extra,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-kid"})


def test_verify_clerk_session_token_accepts_valid_token():
    priv, pub = _rsa_keypair()
    issuer = "https://clerk.example.com"
    token = _encode_clerk_like_token(priv, issuer=issuer)

    mock_signing = MagicMock()
    mock_signing.key = pub
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing

    with patch("app.services.clerk_jwt.get_jwks_client", return_value=mock_client):
        claims = verify_clerk_session_token(token)

    assert claims["sub"] == "user_2abc"
    assert claims["iss"] == issuer
    mock_client.get_signing_key_from_jwt.assert_called_once_with(token)


def test_verify_clerk_session_token_rejects_wrong_signature():
    priv_a, _ = _rsa_keypair()
    _, pub_b = _rsa_keypair()
    issuer = "https://clerk.example.com"
    token = _encode_clerk_like_token(priv_a, issuer=issuer)

    mock_signing = MagicMock()
    mock_signing.key = pub_b
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing

    with patch("app.services.clerk_jwt.get_jwks_client", return_value=mock_client):
        with pytest.raises(ClerkJWTError):
            verify_clerk_session_token(token)


def test_verify_clerk_session_token_rejects_expired():
    priv, pub = _rsa_keypair()
    issuer = "https://clerk.example.com"
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user_2abc",
        "iss": issuer,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    token = jwt.encode(payload, priv, algorithm="RS256", headers={"kid": "test-kid"})

    mock_signing = MagicMock()
    mock_signing.key = pub
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing

    with patch("app.services.clerk_jwt.get_jwks_client", return_value=mock_client):
        with pytest.raises(ClerkJWTError):
            verify_clerk_session_token(token)


def test_verify_clerk_session_token_rejects_missing_iss():
    priv, _pub = _rsa_keypair()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": "user_x", "iat": now, "exp": now + timedelta(hours=1)},
        priv,
        algorithm="RS256",
    )

    with pytest.raises(ClerkJWTError, match="missing iss"):
        verify_clerk_session_token(token)


def test_verify_clerk_session_token_rejects_missing_sub_after_verify():
    priv, pub = _rsa_keypair()
    issuer = "https://clerk.example.com"
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"iss": issuer, "iat": now, "exp": now + timedelta(hours=1)},
        priv,
        algorithm="RS256",
        headers={"kid": "test-kid"},
    )

    mock_signing = MagicMock()
    mock_signing.key = pub
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing

    with patch("app.services.clerk_jwt.get_jwks_client", return_value=mock_client):
        with pytest.raises(ClerkJWTError, match="missing sub"):
            verify_clerk_session_token(token)


def test_verify_clerk_session_token_rejects_empty_token():
    with pytest.raises(ClerkJWTError, match="missing token"):
        verify_clerk_session_token("")
