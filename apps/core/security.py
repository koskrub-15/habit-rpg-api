from datetime import datetime, timedelta, timezone
from typing import Any, Literal
import uuid

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from apps.core.config import settings

TokenType = Literal["access", "refresh"]

password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2."""
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its Argon2 hash."""
    return password_hash.verify(plain, hashed)


def _create_token(
    subject: int | str, token_type: TokenType, lifetime: timedelta
) -> str:
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": datetime.now(timezone.utc) + lifetime,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str, token_type: TokenType) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub", "type", "jti"]},
        )
    except jwt.InvalidTokenError:
        return None
    if payload["type"] != token_type:
        return None
    return payload


def create_access_token(
    subject: int | str, expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT access token."""
    return _create_token(
        subject,
        "access",
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    subject: int | str, expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT refresh token."""
    return _create_token(
        subject,
        "refresh",
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> str | None:
    """Decode a JWT access token and return the subject claim.

    Returns:
        User id as string, or None if token is invalid/expired.
    """
    payload = _decode_token(token, "access")
    return payload["sub"] if payload else None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """Decode a JWT refresh token and return the full payload.

    Returns:
        Payload dict with 'sub', 'jti', 'exp' keys, or None if invalid/expired.
    """
    return _decode_token(token, "refresh")
