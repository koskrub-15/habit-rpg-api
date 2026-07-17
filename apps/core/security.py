from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from apps.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its Argon2 hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: int | str, expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: int | str, expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT refresh token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Decode a JWT access token and return the subject claim.

    Returns:
        User id as string, or None if token is invalid/expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict | None:
    """Decode a JWT refresh token and return the full payload.

    Returns:
        Payload dict with 'sub', 'jti', 'exp' keys, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
