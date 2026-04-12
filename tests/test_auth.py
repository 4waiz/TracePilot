"""
Unit tests for authentication utilities (password hashing, JWT tokens, roles).
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    ALGORITHM,
)
from backend.config import settings


# ── Password hashing ───────────────────────────────────────────────────────


def test_password_hashing():
    """Hashing a password should produce a bcrypt hash that is not the plaintext."""
    plain = "SecureP@ss123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2")  # bcrypt prefix


def test_password_verification_wrong():
    """Verifying with the wrong password should return False."""
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_password_verification_correct():
    """Verifying with the correct password should return True."""
    plain = "correct-password"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


# ── JWT tokens ──────────────────────────────────────────────────────────────


def test_token_creation():
    """Creating a token should return a non-empty string."""
    token = create_access_token(
        data={"sub": "testuser", "user_id": 1, "role": "operator"},
        expires_delta=timedelta(minutes=30),
    )
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_decode():
    """A valid token should decode back to the original claims."""
    payload_in = {"sub": "testuser", "user_id": 42, "role": "admin"}
    token = create_access_token(data=payload_in, expires_delta=timedelta(minutes=30))
    payload_out = decode_token(token)

    assert payload_out["sub"] == "testuser"
    assert payload_out["user_id"] == 42
    assert payload_out["role"] == "admin"
    assert "exp" in payload_out


def test_token_decode_invalid():
    """Decoding a tampered token should raise HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        decode_token("this.is.not.a.valid.token")
    assert exc_info.value.status_code == 401


# ── Role check ──────────────────────────────────────────────────────────────


def test_role_check():
    """Tokens should carry the role claim correctly."""
    for role in ("operator", "supervisor", "admin"):
        token = create_access_token(
            data={"sub": "user", "user_id": 1, "role": role},
            expires_delta=timedelta(minutes=10),
        )
        decoded = decode_token(token)
        assert decoded["role"] == role
